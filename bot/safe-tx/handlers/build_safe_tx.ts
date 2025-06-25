import { Interface } from "@ethersproject/abi";
import { BigNumber } from "@ethersproject/bignumber";

import { LAGOON_ABI } from "./lagoon_abi.ts";
console.log("✅ ABI loaded:", typeof LAGOON_ABI);
console.log(
  "ABI length:",
  Array.isArray(LAGOON_ABI) ? LAGOON_ABI.length : "Not an array"
);

export function buildSafeTransactionData(
  method: string,
  args: string[],
  contractAddress: string
) {
  const iface = new Interface(LAGOON_ABI);

  let data: string;

  switch (method) {
    case "settleDeposit":
      if (args.length !== 1) throw new Error("settleDeposit requires 1 arg");
      data = iface.encodeFunctionData("settleDeposit", [
        BigNumber.from(args[0]),
      ]);
      break;

    case "updateNewTotalAssets":
      if (args.length !== 1)
        throw new Error("updateNewTotalAssets requires 1 arg");
      data = iface.encodeFunctionData("updateNewTotalAssets", [
        BigNumber.from(args[0]),
      ]);
      break;

    case "claimSharesOnBehalf":
      if (args.length < 1)
        throw new Error("claimSharesOnBehalf requires at least 1 address");
      data = iface.encodeFunctionData("claimSharesOnBehalf", [args]);
      break;

    default:
      throw new Error(`Unsupported method: ${method}`);
  }

  return {
    to: contractAddress,
    data,
    value: "0",
  };
}
