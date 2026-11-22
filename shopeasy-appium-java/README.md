# ShopEasy Appium Java Test on Device Farm

This project contains Java-based Appium automation (Appium Java Client 9.x + Selenium 4.x) tailored for the **ShopEasy** Android app on your local **Appium Device Farm**.

---

### Configuration Details

- **Device Farm Hub URL**: `http://127.0.0.1:31337/wd/hub`
- **Target Device**: `LAVA LXX504` (UDID: `AGN2DK23IB022871`, Android 15)
- **Application**: `Shopeasy.apk` (Device Farm Asset: `file-1795353402295.apk`)
- **Package / Activity**:
  - `appPackage`: `com.example.shopeasy`
  - `appActivity`: `com.example.shopeasy.MainActivity`

---

### Prerequisites

1. **Appium Hub Running**:
   Ensure your central hub is active with the `device-farm` plugin:
   ```bash
   cd /Users/upendra.chouhan/.gemini/antigravity/scratch/mobile-device-farm-perf
   appium server --use-plugins=device-farm --config ./hub-config.json
   ```

2. **Lava Device Connected**:
   Verify the real device is visible to adb:
   ```bash
   adb devices
   # Output should show: AGN2DK23IB022871 device
   ```

---

### Running the Test

#### Option 1: IntelliJ IDEA / Eclipse / VS Code
1. Open the `shopeasy-appium-java` folder in your IDE.
2. Allow Maven to import dependencies from `pom.xml`.
3. Open `src/test/java/com/example/shopeasy/ShopEasyDeviceFarmTest.java`.
4. Right-click and choose **Run 'ShopEasyDeviceFarmTest'** (or run `main(String[] args)`).

#### Option 2: Command Line via Maven
If Maven is installed (`brew install maven` or existing `mvn`):
```bash
cd shopeasy-appium-java
mvn clean test
```
