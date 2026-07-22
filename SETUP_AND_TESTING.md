# Setup and Testing Guide (Linux)

This guide provides instructions on how to set up the new version of `looker-deployer` (which uses `looker-cli` instead of the legacy `gzr` and Looker Python SDK) on a Linux computer and how to perform manual and automated testing.

---

## 1. Prerequisites & Environment Setup

### Step 1: Install Python >= 3.10
Ensure you have Python 3.10 or newer installed. You can check your version using:
```bash
python3 --version
```

### Step 2: Install Pipenv
`looker-deployer` uses `Pipenv` for managing virtual environments and dependencies. Install it using `pip`:
```bash
pip3 install --user pipenv
```

### Step 3: Install `looker-cli` (Go-based CLI)
`looker-deployer` now calls the Go-based `looker-cli` under the hood. You must install `looker-cli` and ensure it is accessible in your system's `PATH`.

To download and install the latest Linux binary:
```bash
# Download the binary (example using looker-cli v0.1.0; check repo for latest)
curl -L https://github.com/looker-open-source/looker-cli/releases/latest/download/looker-cli-linux-amd64 -o looker-cli

# Make the binary executable
chmod +x looker-cli

# Move it into your PATH
sudo mv looker-cli /usr/local/bin/
```
Verify the installation by running:
```bash
looker-cli version
```

---

## 2. Setting Up Looker Deployer

### Step 1: Clone or Checkout the Branch
Make sure you are on the `fix-looker-cli` branch:
```bash
git checkout fix-looker-cli
```

### Step 2: Install Project Dependencies
Run `pipenv` to create the virtual environment and install the required libraries:
```bash
pipenv install --dev
```

### Step 3: Configure `looker.ini`
Create a `looker.ini` file in the root of the repository to store api keys for your Looker instances (do **not** commit this file):
```ini
[Dev]
base_url=https://your-dev-looker.com:19999
client_id=your_dev_client_id
client_secret=your_dev_client_secret

[Prod]
base_url=https://your-prod-looker.com:19999
client_id=your_prod_client_id
client_secret=your_prod_client_secret
```

---

## 3. Running Automated Tests

To run the comprehensive test suite (which mocks the new CLI commands):
```bash
pipenv run python3 -m pytest -v
```

All 250+ unit, adversarial, and stress tests should pass successfully.

---

## 4. Manual Testing

`looker-deployer` is invoked using the `ldeploy` command. Run the following examples using `pipenv run ldeploy` to execute manual verification against your instances.

### 4.1 Boards Deployment
Deploy a specific board from your Dev environment to your Prod environment:
```bash
pipenv run ldeploy boards --source Dev --target Prod --board "Executive Dashboard"
```

### 4.2 Connections Deployment
Deploy database connections from Dev to Prod:
```bash
pipenv run ldeploy connections --source Dev --target Prod
```
*Optional: Use `--include-password` to pass password credentials configured in `looker.ini`.*

### 4.3 Content Deployment (Dashboard and Looks)

**Step 1: Export content locally**
Download content from your source Dev environment into a local folder:
```bash
pipenv run ldeploy content export --env Dev --local-target ./backup_content --folders Shared
```

**Step 2: Import content to Target**
Deploy the locally saved content into your target Prod environment:
```bash
pipenv run ldeploy content import --env Prod --folders ./backup_content/Shared
```

### 4.4 Permissions and Roles Deployment
Deploy permissions, models, and roles in sequence:

```bash
# 1. Deploy Permission Sets
pipenv run ldeploy permission_sets --source Dev --target Prod

# 2. Deploy Model Sets
pipenv run ldeploy model_sets --source Dev --target Prod

# 3. Deploy Roles
pipenv run ldeploy roles --source Dev --target Prod
```

### 4.5 Groups & Mappings Deployment
Deploy groups and nesting structures:

```bash
# 1. Deploy User Groups
pipenv run ldeploy groups --source Dev --target Prod

# 2. Deploy Group-in-Group hierarchy
pipenv run ldeploy group_in_group --source Dev --target Prod

# 3. Deploy Role-to-Group mappings
pipenv run ldeploy role_to_group --source Dev --target Prod
```

### 4.6 User Attributes Deployment
Deploy user attributes config:
```bash
pipenv run ldeploy user_attributes --source Dev --target Prod
```

---

## 5. Troubleshooting

- **Command Not Found (`looker-cli`):** Ensure the `looker-cli` binary is executable (`chmod +x`) and located in a directory listed in your `$PATH` (like `/usr/local/bin`).
- **Authentication Failures:** The tool reads credentials from `looker.ini` and automatically maps them to environment variables (`LOOKERSDK_BASE_URL`, etc.) before calling out to the CLI. Double-check that your API credentials have the correct admin permissions.
- **Python Import Errors:** Always prefix commands with `pipenv run` to ensure you are executing within the correct virtual environment context.
