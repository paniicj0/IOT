# Exam Cheat Sheet — Copy `IOTproject` to the Pi

## 0) Set the IP
> Replace with the IP given on the exam day.
```bash
PI_IP=192.168.107.14
```

---

## Terminal 1 — SSH into the Pi and create the folder
```bash
ssh student@192.168.107.148
# password: ftn

mkdir odbranaJovanaTeodora
```

---

## Terminal 2 — Copy project from laptop to Pi
Run on **your laptop** (not inside SSH):
```bash
scp -r IOTproject student@192.168.107.148:~/odbranaJovanaTeodora/
```
---

## Notes
- Password is `ftn`.
- Run `scp` from the **laptop**, not from inside the SSH session.
