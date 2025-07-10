import Safe, { EthersAdapter } from "@safe-global/protocol-kit";
import { SafeTransaction } from "@safe-global/safe-core-sdk-types";
import dotenv from "dotenv";
import { ethers } from "ethers";
import { buildSafeTransactionData } from "./handlers/build_safe_tx";
import { executeSafeTransactionWithRetry } from "./handlers/execute_safe_tx";
import { simulateSafeTransaction } from "./handlers/simulate_safe_tx";
import { updateKeeperStatus } from "./handlers/update_keeper_status";

dotenv.config();

const { Wallet, providers } = ethers;
const { JsonRpcProvider } = providers;

export const SUPPORTED_METHODS = [
  "settleDeposit",
  "updateNewTotalAssets",
  "claimSharesOnBehalf",
  "approve",
];

type ParsedCall = { method: string; contract: string; args: string[] };

function parseBatchedCalls(argv: string[]): {
  method: string;
  contract: string;
  args: string[];
}[][] {
  const result: ParsedCall[][] = [[]];
  let i = 0;

  while (i < argv.length) {
    const method = argv[i];
    const contract = argv[i + 1];
    i += 2;

    const currentArgs: string[] = [];
    while (i < argv.length && !SUPPORTED_METHODS.includes(argv[i])) {
      currentArgs.push(argv[i]);
      i++;
    }

    // Each subarray is a batch of transactions, if we need multiple batches, we just need to add a new subarray
    // Then filter according to the method to recognize the corresponding batch to which the current tx have to be added to
    result[0].push({ method, contract, args: currentArgs });
  }

  return result;
}

async function buildAndSimulateTransaction(
  safeSdk: Safe,
  provider: ethers.providers.JsonRpcProvider,
  batch: ParsedCall[],
  nonce: number
): Promise<SafeTransaction> {
  const txs = batch.map(({ method, contract, args }) =>
    buildSafeTransactionData(method, args, contract, nonce)
  );

  console.log("Creating transaction batch...", txs);

  const safeTx = await safeSdk.createTransaction({ safeTransactionData: txs });

  console.log("Signing transaction...");
  const signedTx = await safeSdk.signTransaction(safeTx);

  console.log("Simulating transaction...");
  const success = await simulateSafeTransaction({
    provider,
    vaultAddress: process.env.VAULT_ADDRESS!,
    safeAddress: process.env.SAFE_ADDRESS!,
    safeTx: signedTx,
    signatures: signedTx.encodedSignatures(),
  });

  if (!success) throw new Error("Simulation failed");

  console.log("Simulation successful, ready for execution");
  return signedTx;
}

async function main() {
  console.log("Script started");

  const args = process.argv.slice(2);

  if (args.length < 3) {
    console.error(
      "Usage: ts-node send_safe_tx.ts <method> <contract> <args...> [repeat...]"
    );
    //process.exit(1);
  }

  const provider = new JsonRpcProvider(process.env.RPC_URL!);
  const signer = new Wallet(process.env.SAFE_OWNER_PRIVATE_KEY!, provider);

  const ethAdapter = new EthersAdapter({
    ethers,
    signerOrProvider: signer,
  });

  // Get network info
  const network = await provider.getNetwork();
  console.log(`Network: ${network.name} (Chain ID: ${network.chainId})`);

  // Check if the Safe address is actually a contract
  const code = await provider.getCode(process.env.SAFE_ADDRESS!);
  if (code === "0x") {
    throw new Error(
      `No contract found at address ${process.env.SAFE_ADDRESS!}`
    );
  }
  console.log(`Contract found at Safe address ${process.env.SAFE_ADDRESS!}`);

  // Try to create Safe SDK with minimal configuration
  const safeSdk = await Safe.create({
    ethAdapter,
    safeAddress: process.env.SAFE_ADDRESS!,
  });

  const parsedCalls = parseBatchedCalls(args);
  console.log("Parsed calls: ", parsedCalls);
  let onChainNonce = await safeSdk.getNonce();
  const justSimulate = process.env.JUST_SIMULATE === "true";

  for (const batch of parsedCalls) {
    if (batch.length === 0) continue;

    let signedTx = await buildAndSimulateTransaction(
      safeSdk,
      provider,
      batch,
      onChainNonce
    );

    if (!justSimulate) {
      const feeData = await provider.getFeeData();
      if (!feeData.maxFeePerGas) {
        throw new Error("Could not fetch current base fee from provider");
      }

      const baseFee = feeData.maxFeePerGas; // ethers.BigNumber
      const priorityFee = ethers.utils.parseUnits("2", "gwei"); // typical tip value

      // recommendedMaxFee = baseFee * 1.3 + priorityFee
      const recommendedMaxFee = baseFee.mul(13).div(10).add(priorityFee);

      const newMaxFeePerGas = ethers.utils.formatUnits(
        recommendedMaxFee,
        "gwei"
      );
      console.log(
        `Calculated recommended maxFeePerGas: ${newMaxFeePerGas} gwei`
      );

      await executeSafeTransactionWithRetry(
        safeSdk,
        signedTx,
        provider,
        onChainNonce,
        newMaxFeePerGas || "20"
      );

      /* 

      let proposedMaxFeePerGas: string | undefined = "20";
      while (!!proposedMaxFeePerGas) {
        proposedMaxFeePerGas = await executeSafeTransactionWithRetry(
          safeSdk,
          signedTx,
          provider,
          onChainNonce,
          proposedMaxFeePerGas
        );

        if (!!proposedMaxFeePerGas) {
          console.log("Proposed max fee per gas: ", proposedMaxFeePerGas);
          onChainNonce = await safeSdk.getNonce();
          signedTx = await buildAndSimulateTransaction(
            safeSdk,
            provider,
            batch,
            onChainNonce
          );
        }
      }
 */
      // Update keeper status
      await updateKeeperStatus(
        network.chainId.toString(),
        process.env.VAULT_ADDRESS!,
        provider
      );
    } else {
      console.log("Just simulated; skipping execution.");
    }

    onChainNonce += 1;
  }
}

main().catch((e) => {
  console.error("Error in send_safe_tx.ts:");
  if (e instanceof Error) {
    console.error(e.stack || e.message);
  } else if (typeof e === "object") {
    console.error(JSON.stringify(e, null, 2));
  } else {
    console.error(String(e));
  }
  return;
  //process.exit(1);
});
