set argv to do shell script "/bin/cat"

set AppleScript's text item delimiters to ASCII character 0
set argv to argv's text items
set AppleScript's text item delimiters to {""}

set theTitle to item 1 of argv
set theDate to date (item 2 of argv)
set theCategory to item 3 of argv
set theText to item 4 of argv
set thePermalink to item 5 of argv

tell application "RapidWeaver" to activate

tell application "System Events"
  tell process "RapidWeaver"
    tell window "johnwiegley.com"
      click button 2 of splitter group 1 of group 1 of splitter group 1 of splitter group 1
      delay 0.1
      
      set the clipboard to theTitle
      keystroke "v" using {command down}
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      
      keystroke (year of theDate as string)
      delay 0.1
      keystroke tab
      delay 0.1
      tell theDate to get its month as integer
      keystroke result as string
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke (day of theDate as string)
      delay 0.1
      keystroke tab
      delay 0.1
      
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      
      keystroke theCategory
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      keystroke tab
      delay 0.1
      
      set the clipboard to theText
      keystroke "v" using {command down}
      delay 0.1
      
      if thePermalink is not "" then
        click checkbox "Permalink:" of tab group 1 of splitter group 1 of group 1 of splitter group 1 of splitter group 1
        delay 0.1
        keystroke tab using command down & option down
        delay 0.1
        keystroke tab using command down & option down
        delay 0.1
        set the clipboard to thePermalink
        keystroke "v" using {command down}
        delay 0.1
        keystroke tab
        delay 0.1
      end if
    end tell
  end tell
end tell
