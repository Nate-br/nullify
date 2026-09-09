rule Generic_Trojan_Dropper {
    meta:
        description = "Detects generic trojan dropper behavior via API imports"
        severity = "HIGH"
        att_and_ck_id = "T1055"
        malware_type = "trojan"
    strings:
        $create_remote_thread = "CreateRemoteThread" ascii wide
        $url_download = "URLDownloadToFile" ascii wide
        $win_exec = "WinExec" ascii wide
    condition:
        uint16(0) == 0x5a4d and ($create_remote_thread and ($url_download or $win_exec))
}
