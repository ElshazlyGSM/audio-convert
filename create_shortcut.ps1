$WshShell = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$Shortcut = $WshShell.CreateShortcut("$desktop\Media Audio Studio Test.lnk")
$Shortcut.TargetPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$Shortcut.Arguments = '"e:\Songs\gui.py"'
$Shortcut.WorkingDirectory = "e:\Songs"
$Shortcut.Save()
Write-Host "Created shortcut successfully!"
