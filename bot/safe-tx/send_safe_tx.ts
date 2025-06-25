import Safe, { EthersAdapter } from "@safe-global/protocol-kit";
import dotenv from "dotenv";
import { ethers } from "ethers";
import { buildSafeTransactionData } from "./handlers/build_safe_tx";

dotenv.config();

const { Wallet, providers } = ethers;
const { JsonRpcProvider } = providers;

console.log("Script started");

const args = process.argv.slice(2);

if (args.length < 3) {
  console.error(
    "Usage: ts-node send_safe_tx.ts <method> <contract> <args...> [repeat...]"
  );
  process.exit(1);
}

function parseBatchedCalls(argv: string[]): {
  method: string;
  contract: string;
  args: string[];
}[] {
  const result = [];
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

    result.push({ method, contract, args: currentArgs });
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
    console.log(`🔗 Network: ${network.name} (Chain ID: ${network.chainId})`);

    // Check if the Safe address is actually a contract
    const code = await provider.getCode(process.env.SAFE_ADDRESS!);
    if (code === "0x") {
      throw new Error(
        `No contract found at address ${process.env.SAFE_ADDRESS!}`
      );
    }
    console.log(`Contract found at ${process.env.SAFE_ADDRESS!}`);

    // Try to create Safe SDK with minimal configuration
    const safeSdk = await Safe.create({
      ethAdapter,
      safeAddress: process.env.SAFE_ADDRESS!,
    });

    const parsedCalls = parseBatchedCalls(args);

    const txs = parsedCalls.map(({ method, contract, args }) =>
      buildSafeTransactionData(method, args, contract)
    );

    const safeTx = await safeSdk.createTransaction({
      safeTransactionData: txs,
    });
    await safeSdk.signTransaction(safeTx);

    const execTx = await safeSdk.executeTransaction(safeTx);
    console.log("Batched Safe tx sent:", execTx.hash);
  } catch (e) {
    console.error("Error in send_safe_tx.ts:");

    if (e instanceof Error) {
      console.error(e.stack || e.message);
    } else if (typeof e === "object") {
      console.error(JSON.stringify(e, null, 2));
    } else {
      console.error(String(e));
    }

    process.exit(1);
  }
})();
