from nullify.core.agents.log_analysis import LogAnalysisAgent
from nullify.core.models import AgentStatus, FileTarget, ScanMode, Severity


class MockRecord:
    def __init__(self, xml_str):
        self._xml_str = xml_str
    def xml(self):
        return self._xml_str

from typing import ClassVar


class MockEvtx:
    mock_records: ClassVar[list] = []
    
    def __init__(self, path):
        self.path = path
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def records(self):
        return self.mock_records

def test_log_analysis_agent(monkeypatch, tmp_path):
    monkeypatch.setattr("nullify.core.agents.log_analysis.Evtx", MockEvtx)
    
    agent = LogAnalysisAgent()
    
    # 1. Non-EVTX file -> SKIPPED
    dummy_path = tmp_path / "not_evtx.bin"
    dummy_path.write_bytes(b"NotElfFi")
    res = agent.analyze(FileTarget(path=dummy_path), ScanMode.STATIC_ONLY)
    assert res.status == AgentStatus.SKIPPED
    assert res.data["reason"] == "not an EVTX file"
    
    # Write valid magic bytes for EVTX
    evtx_path = tmp_path / "test.evtx"
    evtx_path.write_bytes(b"ElfFile\x00\x00\x00\x00\x00")
    
    # 2. Test findings (1102, 7045, 6x 4625 for brute force)
    records = []
    
    # 1102 - Audit log cleared
    records.append(MockRecord('''
    <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System><EventID>1102</EventID></System>
    </Event>
    '''))
    
    # 7045 - Service install
    records.append(MockRecord('''
    <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System><EventID>7045</EventID></System>
      <EventData><Data Name="ServiceName">BadService</Data></EventData>
    </Event>
    '''))
    
    # 4625 x6 (same source) - Brute-force
    for i in range(6):
        records.append(MockRecord(f'''
        <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
          <System>
            <EventID>4625</EventID>
            <TimeCreated SystemTime="2026-09-10T10:0{i}:00Z"/>
          </System>
          <EventData>
            <Data Name="IpAddress">10.0.0.5</Data>
          </EventData>
        </Event>
        '''))
        
    MockEvtx.mock_records = records
    
    res = agent.analyze(FileTarget(path=evtx_path), ScanMode.STATIC_ONLY)
    assert res.status == AgentStatus.COMPLETED
    
    findings = res.findings
    
    titles = [f.title for f in findings]
    assert "Audit log cleared" in titles
    assert "New service installed" in titles
    assert "Brute-force logon detected" in titles
    assert titles.count("Single logon failure") == 6
    
    for f in findings:
        if f.title == "Audit log cleared":
            assert f.severity == Severity.HIGH
            assert "T1070.001" in f.mitre_ids
        elif f.title == "New service installed":
            assert f.severity == Severity.MEDIUM
            assert "T1543.003" in f.mitre_ids
        elif f.title == "Brute-force logon detected":
            assert f.severity == Severity.HIGH
            assert "T1110" in f.mitre_ids
        elif f.title == "Single logon failure":
            assert f.severity == Severity.INFO

    # 3. Test memory cap respected (at most 50k records parsed)
    big_records = [MockRecord("<Event><System><EventID>4688</EventID></System></Event>") for _ in range(50005)]
    MockEvtx.mock_records = big_records
    res = agent.analyze(FileTarget(path=evtx_path), ScanMode.STATIC_ONLY)
    assert res.data["records_parsed"] == 50000
