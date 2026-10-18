# Deploying to AWS

The site runs on two EC2 instances:

| Instance | Security group | Inbound | Role |
| --- | --- | --- | --- |
| `esports-proxy` | `esports-proxy` | 22 and 80 from anywhere | nginx; forwards every request to Flask |
| `esports-flask` | `esports-flask` | 22 and 5000 from `esports-proxy` only | gunicorn + Flask + MySQL 8 (localhost only) |

Each instance clones this repo from GitHub on first boot, so **push your changes to `main` before deploying**, and keep the repo public. The proxy finds the Flask instance's private IP by its `esports-role=flask` tag, which is why it needs `LabInstanceProfile`.

## Prerequisites

- AWS CLI v2, with current Learner Lab credentials in `~/.aws/credentials`. They expire with each lab session, so copy them again from **AWS Details → AWS CLI** every time you start the lab. See [Set your credentials](../README.md#set-your-credentials-every-time-you-start-the-lab) in the README. Check with `aws sts get-caller-identity`.
- For `remote_db.sh` and SSH: the Learner Lab key, saved as `~/.ssh/labsuser.pem` with `chmod 400`.

The scripts default to Learner Lab settings: region `us-east-1`, key pair `vockey`, instance profile `LabInstanceProfile`, and `t3.micro`. Override any of them with `AWS_DEFAULT_REGION`, `KEY_NAME`, `INSTANCE_PROFILE`, or `INSTANCE_TYPE`.

## Deploy

```bash
deploy/deploy.sh
```

It first runs `deploy/make_security_groups.sh` to create the `esports-proxy` and `esports-flask` security groups (groups that already exist are left alone), so you don't need to run that script yourself. It then launches both instances. The Flask user data installs MySQL, creates the tables, and loads the demo data. The script polls `/health` through the proxy until the site answers (usually 5–10 minutes) and prints the URL:

```text
site is up: http://<proxy-public-ip>/
```

Use `http://`, not `https://`. The Flask instance's clock is set to `America/New_York`, so time blocks match the lounge's local time.

If you want a stable name, allocate an Elastic IP, associate it with `esports-proxy`, and register it at [Moravian CS DNS](https://awsdns.moraviancs.click/).

## Reset or clear the data on the live server

`remote_db.sh` SSHes to the Flask instance through the proxy and runs a database script there. The script reads `/etc/esports.env` and connects to MySQL on the same host:

```bash
deploy/remote_db.sh seed --reset              # wipe and reload the demo data (do this before a demo)
deploy/remote_db.sh seed --reset --dataset overwatch  # every desk booked for an Overwatch match now
deploy/remote_db.sh clear -y                  # delete every row
deploy/remote_db.sh clear -y --reservations   # delete only bookings
deploy/remote_db.sh init_db -y                # drop and recreate empty tables
```

The app reads the database on every request, so no restart is needed.

## Tear down

```bash
deploy/teardown.sh                # terminate both instances
deploy/delete_security_groups.sh  # optional: also remove the security groups
```

Release any Elastic IP you allocated; it is billed while allocated.

## Launching from the console instead

1. Create the security groups first, either by running `deploy/make_security_groups.sh` or by creating them in the console with the inbound rules in the table at the top of this page.
2. Launch the Flask instance before the proxy: Amazon Linux 2023, security group `esports-flask`, tags `Name=esports-flask` and `esports-role=flask`, user data = `deploy/userdata-flask.sh` with `__DB_PASSWORD__` replaced by a password.
3. Launch the proxy: Amazon Linux 2023, security group `esports-proxy`, tag `Name=esports-proxy`, **IAM instance profile `LabInstanceProfile`**, user data = `deploy/userdata-nginx.sh`.

## Checking an instance

```bash
ssh -i ~/.ssh/labsuser.pem ec2-user@<proxy-public-ip>
sudo tail -n 50 /var/log/cloud-init-output.log   # user data output
systemctl status nginx
curl -s http://<flask-private-ip>:5000/health
```

To reach the Flask instance, jump through the proxy:

```bash
ssh -i ~/.ssh/labsuser.pem -J ec2-user@<proxy-public-ip> ec2-user@<flask-private-ip>
systemctl status esports
systemctl status mysqld
journalctl -u esports -n 50
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `deploy.sh` says esports instances already exist | An earlier deploy is still running | `deploy/teardown.sh`, then deploy again |
| 502 Bad Gateway, or `deploy.sh` times out on `/health` | Flask user data failed (often MySQL install or `git clone`), or gunicorn is down | Jump through the proxy and read `/var/log/cloud-init-output.log` on Flask **before** tearing down. Also check `systemctl status mysqld` and `journalctl -u esports` |
| Site never comes up after a MySQL deploy | `main` on GitHub still has the old SQLite app, or only part of the migration was pushed | Push every MySQL commit (app, tests, deploy) to `main`, then `teardown.sh` and `deploy.sh` again |
| The nginx welcome page appears | The proxy's user data failed before writing `nginx.conf` | Check `/var/log/cloud-init-output.log` on the proxy; "no running instance tagged esports-role=flask" means the tag or `LabInstanceProfile` is missing |
| `git clone` fails in the log | The repo is private, or the commit was not pushed | Make the repo public and push to `main` |
| No reservations show as booked | The demo data was seeded on an earlier day | `deploy/remote_db.sh seed --reset` |
| `remote_db.sh`: permission denied (publickey) | Wrong key file | `KEY_FILE=path/to/key.pem deploy/remote_db.sh ...` |
| Learner Lab session ended and the site is gone | Instances stop when the lab ends; the proxy's public IP changes on restart | Start the lab, then `teardown.sh` and `deploy.sh` for a fresh setup |

## Updating a running deployment

User data runs only on first boot. To pick up new commits, tear down and deploy again. `deploy.sh` generates a new MySQL password each time. Bookings made on the old instances are lost. Pointing `ESPORTS_DB_HOST` at an RDS MySQL 8 endpoint later does not require an application change.
