from fabric import task

# -------------------------------
# Pretty Output Helpers
# -------------------------------
def section(title):
    print("\n" + "#" * 50)
    print(f"# {title}")
    print("#" * 50)


# -------------------------------
# Basic Tasks
# -------------------------------
@task
def greetings(c, msg="morning"):
    print(f"Good {msg}")


@task
def system_info(c):
    section("SYSTEM INFO")

    c.run("hostname", echo=True)
    c.run("uptime", echo=True)
    c.run("df -h", echo=True)
    c.run("free -m", echo=True)


@task
def remote_exec(c):
    section("REMOTE EXECUTION")

    c.run("hostname", echo=True)
    c.run("uptime", echo=True)
    c.run("df -h", echo=True)
    c.run("free -m", echo=True)

    # Install tools
    if c.run("which yum", warn=True, hide=True).ok:
        c.sudo("yum install -y unzip zip wget")
    else:
        c.sudo("apt update && apt install -y unzip zip wget")

    c.run("zip --version", echo=True)


# -------------------------------
# Web Deployment Task
# -------------------------------
@task
def web_setup(c, weburl, dirname):
    section("INSTALL DEPENDENCIES")

    # Detect OS
    if c.run("which yum", warn=True, hide=True).ok:
        c.sudo("yum install -y httpd wget unzip")
        service = "httpd"
    else:
        c.sudo("apt update && apt install -y apache2 wget unzip")
        service = "apache2"

    section("START & ENABLE SERVICE")

    c.sudo(f"systemctl start {service}")
    c.sudo(f"systemctl enable {service}")

    section("DOWNLOAD WEBSITE")

    c.run(f"wget -O website.zip {weburl}", echo=True)
    c.run("unzip -o website.zip", echo=True)

    section("DEPLOY WEBSITE")

    # Copy files directly (no zip/put issues)
    c.sudo(f"cp -r {dirname}/* /var/www/html/")

    section("RESTART SERVICE")

    c.sudo(f"systemctl restart {service}")

    section("DONE ✅ WEBSITE DEPLOYED SUCCESSFULLY")
