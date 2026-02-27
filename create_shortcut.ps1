$ws = New-Object -ComObject WScript.Shell
$startup = $ws.SpecialFolders('Startup')
$shortcut = $ws.CreateShortcut("$startup\WeightTracker.lnk")
$shortcut.TargetPath = (Get-Command pythonw).Source
$shortcut.Arguments = 'tray.pyw'
$shortcut.WorkingDirectory = 'E:\WeightTracker'
$shortcut.Description = 'WeightTracker - Nutrition Tracker'
$shortcut.Save()
Write-Output "Shortcut created at: $startup\WeightTracker.lnk"
