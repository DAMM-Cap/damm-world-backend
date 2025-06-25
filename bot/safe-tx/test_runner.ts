console.log("test_runner.ts started");

import { buildSafeTransactionData } from "./handlers/build_safe_tx.ts";

console.log("import worked");

const tx = buildSafeTransactionData(
  "updateNewTotalAssets",
  ["1000"],
  "0xVault"
);
console.log("tx built:", tx);
