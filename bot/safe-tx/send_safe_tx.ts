import Safe, { EthersAdapter } from "@safe-global/protocol-kit";
import { SafeTransaction } from "@safe-global/safe-core-sdk-types";
import dotenv from "dotenv";
import { ethers } from "ethers";
import { buildSafeTransactionData } from "./handlers/build_safe_tx";
import { simulateSafeTransaction } from "./handlers/simulate_safe_tx";

dotenv.config();

const { Wallet, providers } = ethers;
const { JsonRpcProvider } = providers;

console.log("Script started");

const args = process.argv.slice(2);

if (args.length < 3) {
  console.error(
    "Usage: ts-node send_safe_tx.ts <method> <contract> <args...> [repeat...]"
  );
  //process.exit(1);
}

function parseBatchedCalls(argv: string[]): {
  method: string;
  contract: string;
  args: string[];
}[][] {
  const result: { method: string; contract: string; args: string[] }[][] = [
    [],
    [],
    [],
  ];
  let i = 0;

  while (i < argv.length) {
    const method = argv[i];
    const contract = argv[i + 1];
    i += 2;

    const currentArgs: string[] = [];
    while (
      i < argv.length &&
      ![
        "settleDeposit",
        "updateNewTotalAssets",
        "claimSharesOnBehalf",
      ].includes(argv[i])
    ) {
      currentArgs.push(argv[i]);
      i++;
    }

    // Txs are single triggered in case of updateNewTotalAssets and settleDeposit, and batched otherwise
    if (method === "updateNewTotalAssets") {
      result[0].push({ method, contract, args: currentArgs });
    } else if (method === "settleDeposit") {
      result[1].push({ method, contract, args: currentArgs });
    } else {
      result[2].push({ method, contract, args: currentArgs });
    }
  }

  return result;
}

(async () => {
  try {
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

    const txs = parsedCalls.map((txs) =>
      txs.map(({ method, contract, args }) =>
        buildSafeTransactionData(method, args, contract)
      )
    );

    const justSimulate = process.env.JUST_SIMULATE === "true";

    let safeTx: SafeTransaction[] = [];
    for (let i = 0; i < txs.length; i++) {
      if (txs[i].length === 0) {
        continue;
      }
      console.log("Creating transaction... ");
      safeTx[i] = await safeSdk.createTransaction({
        safeTransactionData: txs[i],
      });
      await safeSdk.signTransaction(safeTx[i]);

      console.log("Simulating transaction...");
      const success = await simulateSafeTransaction({
        provider,
        vaultAddress: process.env.VAULT_ADDRESS!,
        safeAddress: process.env.SAFE_ADDRESS!,
        safeTx: safeTx[i],
      });

      if (!success) {
        console.error("Simulation failed. Aborting execution.");
        return;
      }

      console.log("Simulation successful, proceeding with execution...");

      if (!justSimulate) {
        const execTx = await safeSdk.executeTransaction(safeTx[i]);
        console.log("Batched Safe tx sent:", execTx.hash);
      } else {
        console.log("Just Simulated!");
      }
    }
  } catch (e) {
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
  }
})();
