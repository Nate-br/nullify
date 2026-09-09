rule Generic_Rootkit {
    meta:
        description = "Detects generic rootkit indicators"
        severity = "HIGH"
        att_and_ck_id = "T1547.003"
        malware_type = "rootkit"
    strings:
        $load1 = "NtLoadDriver" ascii wide
        $load2 = "ZwLoadDriver" ascii wide
        $io = "DeviceIoControl" ascii wide
    condition:
        uint16(0) == 0x5a4d and ($io and any of ($load*))
}
