rule Generic_Ransomware {
    meta:
        description = "Detects generic ransomware indicators"
        severity = "CRITICAL"
        att_and_ck_id = "T1486"
        malware_type = "ransomware"
    strings:
        $crypt1 = "CryptEncrypt" ascii wide
        $crypt2 = "CryptGenKey" ascii wide
        $find1 = "FindFirstFile" ascii wide
        $note1 = "your files have been encrypted" nocase ascii wide
        $note2 = "readme for decrypt" nocase ascii wide
        $note3 = "send btc" nocase ascii wide
    condition:
        uint16(0) == 0x5a4d and 
        (($crypt1 and $crypt2 and $find1) or any of ($note*))
}
