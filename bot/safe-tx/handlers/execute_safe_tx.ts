import Safe from "@safe-global/protocol-kit";
import { SafeTransaction } from "@safe-global/safe-core-sdk-types";
import { ethers } from "ethers";

const maxFeePerGasLimitConst = 100;

async function waitForTransactionConfirmation(
  provider: ethers.providers.JsonRpcProvider,
  txHash: string,
  maxAttempts: number = 30
): Promise<ethers.providers.TransactionReceipt> {
  console.log(`Waiting for transaction confirmation: ${txHash}`);

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const receipt = await provider.getTransactionReceipt(txHash);
      if (receipt) {
        console.log(`Transaction confirmed in block ${receipt.blockNumber}`);
        return receipt;
      }
    } catch (error) {
      console.log(
        `Attempt ${attempt}/${maxAttempts}: Transaction not yet confirmed...`
      );
    }

    // Wait 2 seconds before next attempt
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  throw new Error(
    `Transaction ${txHash} not confirmed after ${maxAttempts} attempts`
  );
}

export async function executeSafeTransactionWithRetry(
  safeSdk: Safe,
  signedTx: SafeTransaction,
  provider: ethers.providers.JsonRpcProvider,
  onChainNonce: number,
  maxFeePerGas: string
) {
  try {
    const execTx = await safeSdk.executeTransaction(signedTx, {
      gasLimit: 500000, // Set explicit gas limit
      maxFeePerGas: ethers.utils.parseUnits(maxFeePerGas, "gwei").toString(),
      maxPriorityFeePerGas: ethers.utils.parseUnits("2", "gwei").toString(),
    });
    console.log("Batched Safe tx sent:", execTx.hash);

    // Wait for transaction confirmation and check receipt
    try {
      const receipt = await waitForTransactionConfirmation(
        provider,
        execTx.hash
      );

      if (receipt.status === 1) {
        console.log("Transaction executed successfully!");
        console.log(`Gas used: ${receipt.gasUsed.toString()}`);
        console.log(`Block number: ${receipt.blockNumber}`);
      } else {
        console.error("Transaction reverted!");
        console.error(`Transaction hash: ${execTx.hash}`);
        console.error(`Block number: ${receipt.blockNumber}`);
        throw new Error("Transaction reverted on-chain");
      }
    } catch (confirmationError) {
      console.error("Transaction confirmation failed:", confirmationError);
      throw confirmationError;
    }
  } catch (executionError: any) {
    // Handle "already known" error gracefully
    if (
      executionError.message &&
      executionError.message.includes("already known")
    ) {
      console.log(
        "Transaction already submitted to network (already known error)"
      );
      console.log(
        "This usually means the transaction was executed successfully in a previous run"
      );
      console.log("Checking if transaction exists on-chain...");

      // Try to get the transaction hash from the error or check recent transactions
      try {
        // Get the current nonce to check if it was incremented
        const currentNonce = await safeSdk.getNonce();
        if (currentNonce > onChainNonce) {
          console.log(
            `Nonce was incremented (${onChainNonce} -> ${currentNonce}), transaction likely executed successfully`
          );
          console.log("Transaction execution completed successfully!");
        } else {
          console.log(
            "Nonce unchanged, transaction may still be pending or failed."
          );
          if (Number(maxFeePerGas) < maxFeePerGasLimitConst) {
            console.log("Speeding up with double gas price...");
            executeSafeTransactionWithRetry(
              safeSdk,
              signedTx,
              provider,
              onChainNonce,
              String(Number(maxFeePerGas) * 2)
            );
          } else {
            throw executionError;
          }
        }
      } catch (nonceError) {
        console.log("Could not verify nonce, treating as execution failure");
        throw executionError;
      }
    } else {
      // Re-throw other execution errors
      throw executionError;
    }
  }
}
