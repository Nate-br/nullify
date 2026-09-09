rule Generic_Persistence {
    meta:
        description = "Detects persistence mechanisms like Run keys"
        severity = "MEDIUM"
        att_and_ck_id = "T1547.001"
        malware_type = "persistence"
    strings:
        $runkey = "Software\\Microsoft\\Windows\\CurrentVersion\\Run" nocase ascii wide
        $schtasks = "schtasks /create" nocase ascii wide
    condition:
        uint16(0) == 0x5a4d and any of them
}
