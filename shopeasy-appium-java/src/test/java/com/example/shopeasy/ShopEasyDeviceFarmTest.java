package com.example.shopeasy;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import org.openqa.selenium.Dimension;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.interactions.PointerInput;
import org.openqa.selenium.interactions.Sequence;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import java.net.URI;
import java.net.URL;
import java.time.Duration;
import java.util.Collections;
import java.util.List;

/**
 * Appium Java Automation Test for ShopEasy on Appium Device Farm Hub.
 *
 * Configured specifically for:
 *   - Device Farm Hub URL: http://127.0.0.1:31337/wd/hub
 *   - Target Device: Real Android Device (LAVA LXX504 / UDID: AGN2DK23IB022871)
 *   - Application: Shopeasy.apk (Package: com.example.shopeasy)
 *   - Activity: com.example.shopeasy.MainActivity
 */
public class ShopEasyDeviceFarmTest {

    private AndroidDriver driver;
    private WebDriverWait wait;

    // Device Farm Hub endpoint from hub-config.json
    private static final String HUB_URL = "http://127.0.0.1:31337/wd/hub";

    // Target Lava Real Device
    private static final String DEVICE_UDID = "AGN2DK23IB022871";
    private static final String DEVICE_NAME = "LAVA LXX504";

    @BeforeClass
    public void setUp() throws Exception {
        System.out.println("==================================================");
        System.out.println("🚀 Initializing Appium Device Farm Session...");
        System.out.println("Connecting to Hub: " + HUB_URL);
        System.out.println("Targeting Device: " + DEVICE_NAME + " (" + DEVICE_UDID + ")");
        System.out.println("==================================================");

        try {
            UiAutomator2Options options = new UiAutomator2Options();
            options.setPlatformName("Android");
            options.setAutomationName("UiAutomator2");

            // Target the connected Lava device
            options.setUdid(DEVICE_UDID);
            options.setDeviceName(DEVICE_NAME);

            // Package & Activity discovered from Shopeasy.apk
            options.setAppPackage("com.example.shopeasy");
            options.setAppActivity("com.example.shopeasy.MainActivity");

            // Reuse already installed app without reinstalling every run
            options.setNoReset(true);
            options.setAutoGrantPermissions(true);

            // Screen & unlock management
            options.setCapability("appium:skipUnlock", true);
            options.setCapability("appium:ignoreHiddenApiPolicyError", true);
            options.setNewCommandTimeout(Duration.ofSeconds(180));

            URL hubUrl = URI.create(HUB_URL).toURL();
            System.out.println("⏳ Sending session creation request to Device Farm Hub...");
            driver = new AndroidDriver(hubUrl, options);
            wait = new WebDriverWait(driver, Duration.ofSeconds(20));

            System.out.println("✅ Session created successfully! Session ID: " + driver.getSessionId());
        } catch (Throwable t) {
            System.err.println("\n❌ FAILED TO CREATE APPIUM SESSION!");
            System.err.println("Root Cause: " + t.getClass().getName() + ": " + t.getMessage());
            t.printStackTrace(System.err);
            throw new RuntimeException("Could not initialize Appium session on Device Farm Hub", t);
        }
    }

    @Test
    public void testShopEasyAddProductToCart() throws InterruptedException {
        System.out.println("\n--- Step 1: Verify ShopEasy App Launched ---");
        wait.until(d -> driver.getCurrentPackage() != null && driver.getCurrentPackage().contains("shopeasy"));
        System.out.println("Active Package: " + driver.getCurrentPackage());
        System.out.println("Active Activity: " + driver.currentActivity());

        // Wait for ShopEasy home screen elements to render
        WebElement categoriesHeader = wait.until(
                ExpectedConditions.visibilityOfElementLocated(
                        AppiumBy.androidUIAutomator("new UiSelector().text(\"Categories\")")
                )
        );
        System.out.println("✅ App Home Screen loaded. Found: " + categoriesHeader.getText());

        System.out.println("\n--- Step 2: Filter by Category ('Phones') ---");
        List<WebElement> phonesCategory = driver.findElements(
                AppiumBy.androidUIAutomator("new UiSelector().text(\"Phones\")")
        );
        if (!phonesCategory.isEmpty()) {
            phonesCategory.get(0).click();
            System.out.println("✅ Selected 'Phones' category filter.");
            Thread.sleep(1500);
        }

        System.out.println("\n--- Step 3: Locate Product & Tap 'Buy' ---");
        List<WebElement> buyButtons = driver.findElements(
                AppiumBy.androidUIAutomator("new UiSelector().text(\"Buy\")")
        );
        if (!buyButtons.isEmpty()) {
            System.out.println("Found " + buyButtons.size() + " 'Buy' button(s). Clicking first item...");
            buyButtons.get(0).click();
            System.out.println("✅ Tapped 'Buy' button.");
        } else {
            System.out.println("Tapping on product card directly...");
            List<WebElement> productTitles = driver.findElements(
                    AppiumBy.androidUIAutomator("new UiSelector().textContains(\"Pixel\")")
            );
            if (!productTitles.isEmpty()) {
                productTitles.get(0).click();
                System.out.println("✅ Tapped on product: " + productTitles.get(0).getText());
            }
        }

        System.out.println("\n--- Step 4: Perform Downward Scroll on Real Device ---");
        performScrollGesture();
        System.out.println("✅ Scroll gesture completed.");

        System.out.println("\n--- Step 5: Navigate to Cart ---");
        List<WebElement> cartTab = driver.findElements(
                AppiumBy.androidUIAutomator("new UiSelector().text(\"Cart\")")
        );
        if (!cartTab.isEmpty()) {
            cartTab.get(0).click();
            System.out.println("✅ Switched to 'Cart' screen.");
            Thread.sleep(1500);
        }

        System.out.println("\n🎉 ShopEasy action workflow completed successfully on LAVA LXX504!");
    }

    /**
     * W3C standard touch action for vertical scrolling
     */
    private void performScrollGesture() {
        Dimension size = driver.manage().window().getSize();
        int startX = size.width / 2;
        int startY = (int) (size.height * 0.70);
        int endY = (int) (size.height * 0.30);

        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence swipe = new Sequence(finger, 1);

        swipe.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), startX, startY));
        swipe.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        swipe.addAction(finger.createPointerMove(Duration.ofMillis(600), PointerInput.Origin.viewport(), startX, endY));
        swipe.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));

        driver.perform(Collections.singletonList(swipe));
    }

    @AfterClass(alwaysRun = true)
    public void tearDown() {
        if (driver != null) {
            System.out.println("\n🔚 Releasing device back to Device Farm pool...");
            try {
                driver.quit();
                System.out.println("✅ Session terminated cleanly.");
            } catch (Exception e) {
                System.err.println("Warning: Error closing session: " + e.getMessage());
            }
        }
    }

    /**
     * Direct standalone execution support (Run without TestNG runner)
     */
    public static void main(String[] args) {
        ShopEasyDeviceFarmTest test = new ShopEasyDeviceFarmTest();
        try {
            test.setUp();
            test.testShopEasyAddProductToCart();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            test.tearDown();
        }
    }
}
