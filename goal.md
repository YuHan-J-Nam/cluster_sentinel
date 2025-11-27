## Final goal

Have two computers be able to work together from the same "memory"

Option 1: FIFO only works within the single os

Option 2: Use sharedMem -> blocked in linux; also doesn't allow two different computers

Option 3: Use the network

---

### Using the Network

#### Sending data to a webserver

- In the past, used to use the command `telnet`
	- No encryption
	- ID and PW used to login were not encrypted
	- Port 80 is commonly used

**PLAN**

- Launch a temporary net-server
	- Send tasks to said net-server (using `telnet` for example)


