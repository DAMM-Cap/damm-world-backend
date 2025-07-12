import { Interface } from "@ethersproject/abi";
import { BigNumber } from "@ethersproject/bignumber";

import { LAGOON_ABI } from "./lagoon_abi";

export function buildSafeTransactionData(
  method: string,
  args: string[],
  contractAddress: string,
  onChainNonce: number
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

    case "approve":
      if (args.length !== 2) throw new Error("approve requires 2 args");
      data = iface.encodeFunctionData("approve", [
        args[0],
        BigNumber.from(args[1]),
      ]);
      break;

    default:
      throw new Error(`Unsupported method: ${method}`);
  }

  return {
    to: contractAddress,
    data,
    value: "0",
    operation: 0,
    nonce: onChainNonce,
  };
}
