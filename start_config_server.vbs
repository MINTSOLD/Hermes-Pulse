Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Program Files\Hermes Agent"
WshShell.Run "pythonw config_server.py", 0, False
