"""Log Analysis Agent - EVTX parsing and analysis."""
from __future__ import annotations

import datetime
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    Finding,
    ScanMode,
    Severity,
    Target,
)

log = logging.getLogger(__name__)

try:
    from Evtx.Evtx import Evtx
except ImportError:
    Evtx = None

def _strip_ns(tag: str) -> str:
    """Remove namespace from XML tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def _parse_xml(xml_str: str) -> dict[str, Any]:
    """Parse Evtx record XML into a dictionary."""
    root = ET.fromstring(xml_str)
    
    event_dict: dict[str, Any] = {"EventID": None, "SystemTime": None, "EventData": {}}
    
    for child in root:
        child_tag = _strip_ns(child.tag)
        if child_tag == "System":
            for sys_elem in child:
                sys_tag = _strip_ns(sys_elem.tag)
                if sys_tag == "EventID":
                    event_dict["EventID"] = int(sys_elem.text) if sys_elem.text else None
                elif sys_tag == "TimeCreated":
                    sys_time_str = sys_elem.attrib.get("SystemTime")
                    if sys_time_str:
                        try:
                            dt = datetime.datetime.fromisoformat(sys_time_str)
                            event_dict["SystemTime"] = dt.timestamp()
                        except Exception:  # noqa: BLE001
                            event_dict["SystemTime"] = None
        elif child_tag in ("EventData", "UserData"):
            for data_elem in child:
                data_tag = _strip_ns(data_elem.tag)
                if data_tag == "Data":
                    name = data_elem.attrib.get("Name")
                    if name:
                        event_dict["EventData"][name] = data_elem.text
                else:
                    event_dict["EventData"][data_tag] = data_elem.text
                    
    return event_dict


class LogAnalysisAgent(BaseAgent):
    """Analyzes EVTX logs for security events."""
    
    name = "LogAnalysis"
    
    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        if Evtx is None:
            return AgentResult(
                agent=self.name, status=AgentStatus.SKIPPED, data={"reason": "python-evtx not installed"}
            )
            
        path = target.path
        if not path.is_file():
            return AgentResult(
                agent=self.name, status=AgentStatus.SKIPPED, data={"reason": "file not found"}
            )
            
        try:
            with open(path, "rb") as f:
                header = f.read(8)
                if header != b"ElfFile\x00":
                    return AgentResult(
                        agent=self.name, status=AgentStatus.SKIPPED, data={"reason": "not an EVTX file"}
                    )
        except Exception as e:  # noqa: BLE001
            return AgentResult(
                agent=self.name, status=AgentStatus.FAILED, error=f"failed to read file: {e}"
            )
            
        findings: list[Finding] = []
        failed_logons: list[tuple[float, str]] = []
        records_parsed = 0
        
        try:
            with Evtx(str(path)) as evtx:
                for record in evtx.records():
                    if records_parsed >= 50000:
                        break
                        
                    try:
                        xml_str = record.xml()
                        event = _parse_xml(xml_str)
                    except Exception:  # noqa: BLE001, S112
                        continue
                        
                    event_id = event.get("EventID")
                    if not event_id:
                        continue
                        
                    if event_id == 1102:
                        findings.append(Finding(
                            agent=self.name, title="Audit log cleared", severity=Severity.HIGH, mitre_ids=("T1070.001",)
                        ))
                    elif event_id == 7045:
                        svc_name = event["EventData"].get("ServiceName", "Unknown Service")
                        findings.append(Finding(
                            agent=self.name, title="New service installed", detail=f"Service: {svc_name}", severity=Severity.MEDIUM, mitre_ids=("T1543.003",)
                        ))
                    elif event_id == 4720:
                        user = event["EventData"].get("TargetUserName", "Unknown")
                        findings.append(Finding(
                            agent=self.name, title="User account created", detail=f"User: {user}", severity=Severity.INFO, mitre_ids=("T1136.001",)
                        ))
                    elif event_id == 4688:
                        proc = event["EventData"].get("NewProcessName", "Unknown")
                        findings.append(Finding(
                            agent=self.name, title="Process creation", detail=f"Process: {proc}", severity=Severity.INFO
                        ))
                    elif event_id == 4624:
                        pass # Logon success
                    elif event_id == 4625:
                        ip = event["EventData"].get("IpAddress")
                        if not ip or ip == "-":
                            ip = event["EventData"].get("TargetUserName", "Unknown")
                            
                        timestamp = event.get("SystemTime") or 0.0
                        failed_logons.append((timestamp, ip))
                        
                        findings.append(Finding(
                            agent=self.name, title="Single logon failure", detail=f"Source: {ip}", severity=Severity.INFO
                        ))
                    
                    records_parsed += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Evtx parsing error: %s", e)
            
        # Detect brute force: >= 5 failures from same source within 10min
        failed_logons.sort(key=lambda x: x[0])
        
        source_failures: dict[str, list[float]] = defaultdict(list)
        for ts, src in failed_logons:
            if ts:
                source_failures[src].append(ts)
            
        for src, timestamps in source_failures.items():
            for i in range(len(timestamps)):
                start_ts = timestamps[i]
                count = 1
                for j in range(i+1, len(timestamps)):
                    if timestamps[j] - start_ts <= 600:
                        count += 1
                    else:
                        break
                if count >= 5:
                    findings.append(Finding(
                        agent=self.name, title="Brute-force logon detected", detail=f"Source: {src}, {count} failures in 10 mins", severity=Severity.HIGH, mitre_ids=("T1110",)
                    ))
                    break # one brute-force per source is enough
                    
        return AgentResult(
            agent=self.name, status=AgentStatus.COMPLETED, findings=findings, data={"records_parsed": records_parsed}
        )
