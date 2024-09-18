# missed-bolus-detector
Scours nightscout for possible missed boluses, and generates pushover warnings accordingly.

## why
This is a long overdue hack to detect a fairly common pattern and cause of strife.  
Really this ought to be smarter, to detect IOB etc. but sometimes a thing just needs released at version 0.

And, why yes, it was an exercise in rapid machine-assisted prototyping, why do you ask?
I'm actually surprised how little it ended up contributing - but Blank Page Syndrome is real, and a LLM is a powerful rubber duck.

## installation 
doesn't need to be on the nightscout machine- just somewhere accessible

git clone, then
paste in
 - your nightscout API key
 - your pushover.net key & token
   (or comment out the call to `send_po_alert` if you really really don't want to use pushover)

pip3 install requests (or get it some other way)

run it! it will loop forever,
or, better, install it as a service:
 - script to /usr/local/bin
 - add the systemd service file
 - start it
