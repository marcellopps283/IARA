import asyncio
import os
from dotenv import load_dotenv
from skills.e2b_sandbox_skill import execute

load_dotenv()

async def main():
    code = """
import matplotlib.pyplot as plt
import numpy as np

arr = np.random.normal(1, 0.1, 1000)
plt.hist(arr, bins=20)
plt.title("E2B Histogram")
plt.show()
"""
    print("Enviando código para E2B...")
    result = await execute({"code": code})
    print(result[:500] + "..." if len(result) > 500 else result)
    if "data:image/png;base64" in result:
        print("\n[OK] Base64 Image Extracted Successfully")
    else:
        print("\n[FAIL] Failed to extract image")

if __name__ == "__main__":
    asyncio.run(main())
