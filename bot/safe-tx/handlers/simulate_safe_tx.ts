import SafeTransaction from "@safe-global/protocol-kit/dist/src/utils/transactions/SafeTransaction";
import { ethers } from "ethers";

interface TenderlySimulationRequest {
  network_id: string;
  from: string;
  to: string;
  input: string;
  value?: string;
  gas?: number;
  gas_price?: string;
  save?: boolean;
  save_if_fails?: boolean;
}

interface TenderlySimulationResponse {
  transaction: {
    hash: string;
    block_number: number;
    from: string;
    to: string;
    value: string;
    input: string;
    gas: number;
    gas_price: string;
    gas_used: number;
    status: boolean;
  };
  simulation: {
    id: string;
    project_id: string;
    owner_id: string;
    network_id: string;
    block_number: number;
    transaction_index: number;
    from: string;
    to: string;
    input: string;
    gas: number;
    gas_price: string;
    gas_used: number;
    value: string;
    status: boolean;
    error_message?: string;
    method_calls?: any[];
  };
}

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

  // Get network info for Tenderly
  const network = await provider.getNetwork();
  const networkId = network.chainId.toString();

  // Prepare Tenderly simulation request
  const tenderlyRequest: TenderlySimulationRequest = {
    network_id: networkId,
    from: safeAddress,
    to: vaultAddress,
    input: txData.data,
    gas: 500000,
    gas_price: ethers.utils.parseUnits("20", "gwei").toString(),
    save: true,
    save_if_fails: true,
  };

  // Try Tenderly simulation first if API key is available
  if (
    process.env.SIMULATE_WITH_TENDERLY === "true" &&
    process.env.TENDERLY_ACCESS_KEY &&
    process.env.TENDERLY_PROJECT_ID
  ) {
    try {
      console.log("Running Tenderly simulation...");
      const tenderlyResponse = await fetch(
        `https://api.tenderly.co/api/v1/account/${process.env.TENDERLY_ACCOUNT_ID}/project/${process.env.TENDERLY_PROJECT_ID}/simulate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Access-Key": process.env.TENDERLY_ACCESS_KEY,
          },
          body: JSON.stringify(tenderlyRequest),
        }
      );

      if (tenderlyResponse.ok) {
        const simulation: TenderlySimulationResponse =
          await tenderlyResponse.json();

        if (simulation.simulation.status) {
          console.log("Tenderly simulation successful!");
          console.log(`Simulation ID: ${simulation.simulation.id}`);
          console.log(`Gas used: ${simulation.simulation.gas_used}`);
          console.log(
            `View simulation: https://dashboard.tenderly.co/${process.env.TENDERLY_ACCOUNT_ID}/project/simulator/${simulation.simulation.id}`
          );
          return true;
        } else {
          console.error("Tenderly simulation failed!");
          console.error(`Error: ${simulation.simulation.error_message}`);
          console.error(`Simulation ID: ${simulation.simulation.id}`);
          console.error(
            `View simulation: https://dashboard.tenderly.co/${process.env.TENDERLY_ACCOUNT_ID}/project/simulator/${simulation.simulation.id}`
          );
          return false;
        }
      } else {
        console.warn(
          "Tenderly API request failed, falling back to local simulation..."
        );
      }
    } catch (error) {
      console.warn(
        "Tenderly simulation failed, falling back to local simulation:",
        error
      );
    }
  }

  // Fallback to local simulation
  console.log("Running local simulation...");
  const callRequest = {
    to: vaultAddress,
    from: safeAddress,
    data: txData.data,
  };

  try {
    const result = await provider.call(callRequest);
    console.log("Local simulation successful!");
    console.log("Result:", result);
    return true;
  } catch (e: any) {
    console.error("Local simulation failed!");
    console.error("Error:", e);
    const reason = e?.error?.data ?? e?.data ?? "0x";
    console.error("Raw revert reason data:", reason);
    return false;
  }
}
