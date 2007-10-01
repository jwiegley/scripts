set argv to do shell script "/bin/cat"

set AppleScript's text item delimiters to ASCII character 0
set argv to argv's text items
set AppleScript's text item delimiters to {""}

set theTitle to item 1 of argv
set theText to item 2 of argv
set theMetadata to item 3 of argv

tell application "Scrivener" to activate

tell application "System Events"
  tell process "Scrivener"
    tell front window
      keystroke "b" using command down & option down & control down

      keystroke "n" using {command down}
      delay 0.1
      
      set the clipboard to theTitle
      keystroke "v" using {command down}
      delay 0.1
      
      keystroke "e" using command down & option down & control down
      delay 0.1
      set the clipboard to theText
      keystroke "v" using {command down}
      
      keystroke "i" using command down & option down & control down
      delay 0.1
      set the clipboard to theMetadata
      keystroke "v" using {command down}
    end tell
  end tell
end tell
