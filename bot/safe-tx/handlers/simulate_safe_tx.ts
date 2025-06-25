import SafeTransaction from "@safe-global/protocol-kit/dist/src/utils/transactions/SafeTransaction";
import { ethers } from "ethers";

export async function simulateSafeTransaction({
  provider,
  vaultAddress,
  safeAddress,
  safeTx,
}: {
  provider: ethers.providers.JsonRpcProvider;
  vaultAddress: string;
  safeAddress: string;
  safeTx: SafeTransaction;
}): Promise<boolean> {
  const txData = safeTx.data;

  const callRequest = {
    to: vaultAddress,
    from: safeAddress,
    data: txData.data,
  };

  try {
    await provider.call(callRequest);
    return true;
  } catch (e: any) {
    console.error("Simulation failed: ", e);
    const reason = e?.error?.data ?? e?.data ?? "0x";
    console.error("Raw revert reason data:", reason);
    return false;
  }
}
