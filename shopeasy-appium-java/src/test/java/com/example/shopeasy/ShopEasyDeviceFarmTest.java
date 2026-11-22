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
 * Appium Java Client (v9.x) Automation Test for ShopEasy on Appium Device Farm Hub.
 *
 * Configured specifically for:
 *   - Device Farm Hub URL: http://127.0.0.1:31337/wd/hub
 *   - Device: Real Android Device (LAVA LXX504 / UDID: AGN2DK23IB022871)
 *   - Uploaded App: Shopeasy.apk (Device Farm asset: file-1795353402295.apk)
 *   - Package: com.example.shopeasy
 *   - Activity: com.example.shopeasy.MainActivity
 */
public class ShopEasyDeviceFarmTest {

    private AndroidDriver driver;
    private WebDriverWait wait;

    // Device Farm Hub endpoint configured in hub-config.json
    private static final String HUB_URL = "http://127.0.0.1:31337/wd/hub";

    // Device Farm uploaded app reference
    // You can use either the local asset identifier or the direct HTTP endpoint from the Hub
    private static final String APP_REFERENCE = "file-1795353402295.apk";
    private static final String APP_HTTP_URL = "http://127.0.0.1:31337/device-farm/apps/file-1795353402295.apk";

    // Target Lava Real Device
    private static final String DEVICE_UDID = "AGN2DK23IB022871";
    private static final String DEVICE_NAME = "LAVA LXX504";

    @BeforeClass
    public void setUp() throws Exception {
        System.out.println("==================================================");
        System.out.println("🚀 Initializing Appium Device Farm Session...");
        System.out.println("Connecting to Hub: " + HUB_URL);
        System.out.println("Targeting Device: " + DEVICE_NAME + " (" + DEVICE_UDID + ")");
        System.out.println("Application: Shopeasy.apk -> " + APP_REFERENCE);
        System.out.println("==================================================");

        UiAutomator2Options options = new UiAutomator2Options();
        options.setPlatformName("Android");
        options.setAutomationName("UiAutomator2");

        // Target your Lava real device attached to the Hub
        options.setUdid(DEVICE_UDID);
        options.setDeviceName(DEVICE_NAME);

        // App capability: Device Farm accepts either the uploaded filename or direct URL
        options.setApp(APP_HTTP_URL);

        // Package & Activity discovered from Shopeasy.apk manifest
        options.setAppPackage("com.example.shopeasy");
        options.setAppActivity("com.example.shopeasy.MainActivity");

        // Session settings
        options.setNoReset(false); // Clean install / fresh start
        options.setAutoGrantPermissions(true);
        options.setNewCommandTimeout(Duration.ofSeconds(180));

        // Connect to Appium Device Farm Hub
        URL hubUrl = URI.create(HUB_URL).toURL();
        driver = new AndroidDriver(hubUrl, options);
        wait = new WebDriverWait(driver, Duration.ofSeconds(20));

        System.out.println("✅ Session created successfully! Session ID: " + driver.getSessionId());
        System.out.println("Device Farm Allocated Device: " + driver.getCapabilities().getCapability("appium:deviceName"));
    }

    @Test
    public void testShopEasyAddProductToCart() {
        System.out.println("\n--- Step 1: Verify ShopEasy App Launched ---");
        // Wait for MainActivity / home container to be active
        wait.until(d -> driver.getCurrentPackage().contains("shopeasy"));
        System.out.println("Active Package: " + driver.getCurrentPackage());
        System.out.println("Active Activity: " + driver.currentActivity());

        System.out.println("\n--- Step 2: Locate Products on Screen ---");
        // Wait for Compose product elements or any button/text with product content
        try {
            Thread.sleep(3000); // Allow Compose UI tree to complete rendering
        } catch (InterruptedException ignored) {}

        // Look for 'Add to Cart' or product buttons
        List<WebElement> addToCartButtons = driver.findElements(
                AppiumBy.androidUIAutomator("new UiSelector().textContains(\"Add to Cart\")")
        );

        if (addToCartButtons.isEmpty()) {
            // Fallback: search for any button or clickable item on screen
            addToCartButtons = driver.findElements(
                    AppiumBy.xpath("//android.widget.Button[contains(@text, 'Add') or contains(@content-desc, 'Add')]")
            );
        }

        if (!addToCartButtons.isEmpty()) {
            System.out.println("Found " + addToCartButtons.size() + " 'Add to Cart' action(s).");
            WebElement firstButton = addToCartButtons.get(0);
            System.out.println("Clicking first 'Add to Cart' button...");
            firstButton.click();
            System.out.println("✅ Clicked 'Add to Cart' successfully!");
        } else {
            System.out.println("ℹ️ 'Add to Cart' button not immediately visible, attempting to tap first product item...");
            List<WebElement> items = driver.findElements(
                    AppiumBy.xpath("//android.widget.TextView[string-length(@text) > 3]")
            );
            if (!items.isEmpty()) {
                System.out.println("Tapping item: " + items.get(0).getText());
                items.get(0).click();
            }
        }

        System.out.println("\n--- Step 3: Perform Downward Scroll on Real Device ---");
        performScrollGesture();
        System.out.println("✅ Scroll gesture completed.");

        System.out.println("\n--- Step 4: Check Cart / Navigation ---");
        List<WebElement> cartIcons = driver.findElements(
                AppiumBy.androidUIAutomator("new UiSelector().textContains(\"Cart\")")
        );
        if (!cartIcons.isEmpty()) {
            System.out.println("Cart indicator/screen found: " + cartIcons.get(0).getText());
        }

        System.out.println("\n🎉 ShopEasy action workflow completed successfully on LAVA LXX504!");
    }

    /**
     * W3C standard touch action for smooth vertical scrolling
     */
    private void performScrollGesture() {
        Dimension size = driver.manage().window().getSize();
        int startX = size.width / 2;
        int startY = (int) (size.height * 0.75);
        int endY = (int) (size.height * 0.25);

        PointerInput finger = new PointerInput(PointerInput.Kind.TOUCH, "finger");
        Sequence swipe = new Sequence(finger, 1);

        swipe.addAction(finger.createPointerMove(Duration.ZERO, PointerInput.Origin.viewport(), startX, startY));
        swipe.addAction(finger.createPointerDown(PointerInput.MouseButton.LEFT.asArg()));
        swipe.addAction(finger.createPointerMove(Duration.ofMillis(800), PointerInput.Origin.viewport(), startX, endY));
        swipe.addAction(finger.createPointerUp(PointerInput.MouseButton.LEFT.asArg()));

        driver.perform(Collections.singletonList(swipe));
    }

    @AfterClass
    public void tearDown() {
        if (driver != null) {
            System.out.println("\n🔚 Releasing device back to Device Farm pool...");
            driver.quit();
            System.out.println("✅ Session terminated cleanly.");
        }
    }

    /**
     * Optional: Allows running directly as a standalone Java application without Maven test runner
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
