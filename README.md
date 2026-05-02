# 🚀 Fabric DevOps Automation

This project contains automation scripts built with **Fabric** for managing servers and deploying web applications.

---

## 📌 Features

* 🔹 Remote command execution
* 🔹 System information collection
* 🔹 Automated web server setup (Apache/Nginx)
* 🔹 Website deployment from URL

---

## 🛠️ Technologies Used

* Python 3
* Fabric 3
* SSH
* Linux (CentOS / Ubuntu)

---

## 📂 Project Structure

```
fabric-devops/
├── fabfile.py        # Main automation tasks
├── requirements.txt  # Python dependencies
├── scripts/          # Helper scripts
├── configs/          # Config files
├── docs/             # Documentation
```

---

## ⚙️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/Python-files.git
cd Python-files
pip install -r requirements.txt
```

---

## 🚀 Usage

### Run task locally

```bash
fab greetings
```

### Run on remote server

```bash
fab -H user@host system-info
```

### Deploy website

```bash
fab -H user@host web-setup \
  --weburl="https://example.com/site.zip" \
  --dirname="site-folder"
```

---

## 🔐 Requirements

* SSH access to remote server
* Python 3 installed
* Fabric installed

---

## 📈 Future Improvements

* Add Docker deployment
* Integrate CI/CD (GitHub Actions)
* Add logging & error handling

---

## 👨‍💻 Author

Fedia-2211

