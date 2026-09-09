rule Generic_Spyware_Keylogger {
    meta:
        description = "Detects generic spyware and keylogging indicators"
        severity = "HIGH"
        att_and_ck_id = "T1056.001"
        malware_type = "spyware"
    strings:
        $hook = "SetWindowsHookEx" ascii wide
        $key = "GetAsyncKeyState" ascii wide
        $clip = "GetClipboardData" ascii wide
    condition:
        uint16(0) == 0x5a4d and ($hook and ($key or $clip))
}
