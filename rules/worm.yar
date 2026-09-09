rule Generic_Worm {
    meta:
        description = "Detects generic worm indicators"
        severity = "HIGH"
        att_and_ck_id = "T1135"
        malware_type = "worm"
    strings:
        $net1 = "WNetOpenEnum" ascii wide
        $net2 = "WNetEnumResource" ascii wide
        $net3 = "NetShareEnum" ascii wide
        $copy = "CopyFile" ascii wide
    condition:
        uint16(0) == 0x5a4d and ($copy and any of ($net*))
}
