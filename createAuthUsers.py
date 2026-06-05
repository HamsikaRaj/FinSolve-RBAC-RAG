import os
import pandas as pd
from passlib.context import CryptContext

# Use PBKDF2 to avoid bcrypt warnings on some mac/python setups
pwdContext = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

projectDir = os.path.dirname(os.path.abspath(__file__))

hrCsvPath = os.path.join(projectDir, "data", "hr", "hr_data.csv")
authCsvPath = os.path.join(projectDir, "data", "hr", "auth_users.csv")

def makeDemoPassword(employeeId: str) -> str:
    employeeId = (employeeId or "").strip()
    digits = "".join([c for c in employeeId if c.isdigit()])
    last4 = digits[-4:] if len(digits) >= 4 else digits
    return f"Fin@{last4}"

def main():
    if not os.path.exists(hrCsvPath):
        raise FileNotFoundError(f"Missing HR CSV: {hrCsvPath}")

    df = pd.read_csv(hrCsvPath)

    rows = []
    for _, row in df.iterrows():
        employeeId = str(row.get("employee_id", "")).strip()
        if not employeeId:
            continue

        plainPassword = makeDemoPassword(employeeId)
        rows.append(
            {
                "employee_id": employeeId,
                "password_hash": pwdContext.hash(plainPassword),
            }
        )

    outDf = pd.DataFrame(rows)
    outDf.to_csv(authCsvPath, index=False)

    print(f"Created: {authCsvPath}")
    print("Demo password pattern: Fin@<last4digits>")
    print("Example: FINEMP1001 -> Fin@1001")

if __name__ == "__main__":
    main()
