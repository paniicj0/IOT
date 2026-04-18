# Exam Cheat Sheet — Copy `IOTproject` to the Pi

## 0) Set the IP
> Replace with the IP given on the exam day.
```bash
PI_IP=192.168.107.14
```

---

## Terminal 1 — SSH into the Pi and create the folder
```bash
ssh student@$PI_IP
# password: ftn

mkdir -p ~/odbranaJovanaTeodora
exit
```

---

## Terminal 2 — Copy project from laptop to Pi
Run on **your laptop** (not inside SSH):
```bash
scp -r IOTproject student@$PI_IP:~/odbranaJovanaTeodora/
```

---

## (Optional) Verify
```bash
ssh student@$PI_IP
ls -la ~/odbranaJovanaTeodora
```

---

## Notes
- Password is `ftn`.
- Run `scp` from the **laptop**, not from inside the SSH session.
- Folder name is **case-sensitive**: `IOTproject`.
- No spaces in the `scp` destination — must be `student@$PI_IP:~/odbranaJovanaTeodora/`.
