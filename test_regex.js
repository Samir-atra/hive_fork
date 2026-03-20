const prTitle = "fix: resolve EventBus deadlock when concurrent handlers saturate semaphore #2531 (micro-fix)";
const isMicroFix = /micro-fix/i.test(prTitle);
console.log(isMicroFix);
