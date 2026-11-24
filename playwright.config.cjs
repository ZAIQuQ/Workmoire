const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
 testDir:'./tests',testMatch:'browser.spec.cjs',timeout:45000,expect:{timeout:8000},
 workers:1,fullyParallel:false,reporter:'list',
 use:{viewport:{width:1440,height:1000},headless:true,reducedMotion:'reduce',trace:'retain-on-failure'},
 webServer:{
  command:'python3 tests/browser_server.py',
  wait:{stdout:/Synthetic browser server ready (?<WORKMOIRE_TEST_PORT>\d+) (?<WORKMOIRE_TEST_SHARE_PORT>\d+)/},
  gracefulShutdown:{signal:'SIGTERM',timeout:5000},
  timeout:15000
 },
 outputDir:'artifacts/browser-results'
});
