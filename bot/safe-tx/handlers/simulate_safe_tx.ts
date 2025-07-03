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
  signatures,
}: {
  provider: ethers.providers.JsonRpcProvider;
  vaultAddress: string;
  safeAddress: string;
  safeTx: SafeTransaction;
  signatures: string;
}): Promise<boolean> {
  const txData = safeTx.data;

  // Get network info for Tenderly
  const network = await provider.getNetwork();
  const networkId = network.chainId.toString();

  // Try Tenderly simulation first if API key is available
  if (
    process.env.SIMULATE_WITH_TENDERLY === "true" &&
    process.env.TENDERLY_ACCESS_KEY &&
    process.env.TENDERLY_PROJECT_ID
  ) {
    try {
      console.log("Running Tenderly simulation...");

      // Check if this is a Safe execTransaction call, direct MultiSend call, or direct contract call
      const isExecTransaction = txData.data.startsWith("0x6a761202"); // execTransaction function selector
      const isMultiSend = txData.data.startsWith("0x8d80ff0a"); // multiSend function selector
      const isDirectContractCall = !isExecTransaction && !isMultiSend; // Any other function call

      console.log(
        `Transaction data type: ${
          isExecTransaction
            ? "execTransaction"
            : isMultiSend
            ? "multiSend"
            : isDirectContractCall
            ? "directContractCall"
            : "unknown"
        }`
      );

      let tenderlyRequest: TenderlySimulationRequest;

      if (isExecTransaction) {
        // This is a Safe execTransaction call - simulate it directly
        console.log("Simulating Safe execTransaction call");
        tenderlyRequest = {
          network_id: networkId,
          from: safeAddress,
          to: safeAddress, // Safe calling itself
          input: txData.data,
          gas: 500000,
          gas_price: ethers.utils.parseUnits("20", "gwei").toString(),
          save: true,
          save_if_fails: true,
        };
      } else if (isMultiSend) {
        // For MultiSend calls, we need to simulate the Safe's execTransaction method
        // The Safe will then handle the delegate call to MultiSend internally
        console.log(
          "Simulating Safe execTransaction for MultiSend delegate call"
        );

        // Construct the Safe's execTransaction call
        const safeInterface = new ethers.utils.Interface([
          "function execTransaction(address to, uint256 value, bytes calldata data, uint8 operation, uint256 safeTxGas, uint256 baseGas, uint256 gasPrice, address gasToken, address payable refundReceiver, bytes calldata signatures) external returns (bool success)",
        ]);

        const execTransactionData = safeInterface.encodeFunctionData(
          "execTransaction",
          [
            txData.to, // to (MultiSend contract)
            txData.value || "0", // value
            txData.data, // data (MultiSend call data)
            txData.operation, // operation (1 for delegate call)
            0, // safeTxGas
            0, // baseGas
            0, // gasPrice
            "0x0000000000000000000000000000000000000000", // gasToken
            "0x0000000000000000000000000000000000000000", // refundReceiver
            signatures, // Use actual signatures from signed transaction
          ]
        );

        tenderlyRequest = {
          network_id: networkId,
          from: safeAddress,
          to: safeAddress, // Safe calling itself
          input: execTransactionData,
          gas: 500000,
          gas_price: ethers.utils.parseUnits("20", "gwei").toString(),
          save: true,
          save_if_fails: true,
        };
      } else if (isDirectContractCall) {
        // This is a direct contract call (like claimSharesOnBehalf) - simulate it directly
        console.log("Simulating direct contract call");
        tenderlyRequest = {
          network_id: networkId,
          from: safeAddress,
          to: txData.to, // Target contract address
          input: txData.data,
          value: txData.value || "0",
          gas: 500000,
          gas_price: ethers.utils.parseUnits("20", "gwei").toString(),
          save: true,
          save_if_fails: true,
        };
      } else {
        throw new Error("Unknown transaction data type");
      }

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

  // Fallback to individual vault operations simulation
  console.log("Simulating individual vault operations directly...");

  try {
    // Decode the MultiSend data to get individual transactions
    // MultiSend format: 0x8d80ff0a + offset + length + encoded transactions
    const multiSendData = txData.data;
    console.log("MultiSend data:", multiSendData);

    // Skip the function selector (4 bytes) and offset (32 bytes)
    const transactionsData = multiSendData.slice(10); // Remove 0x8d80ff0a + 0x00000000000000000000000000000000000000000000000000000000000000020

    console.log("Transactions data:", transactionsData);

    // Parse the transactions manually
    // Each transaction is: operation (1 byte) + to (20 bytes) + value (32 bytes) + data length (32 bytes) + data
    const transactions = [];
    let offset = 0;

    // Skip the length field (32 bytes)
    offset += 64; // 32 bytes = 64 hex chars

    while (offset < transactionsData.length) {
      if (offset + 85 > transactionsData.length) break; // Minimum transaction size

      const operation = parseInt(
        transactionsData.slice(offset, offset + 2),
        16
      );
      const to = "0x" + transactionsData.slice(offset + 2, offset + 42);
      const value = "0x" + transactionsData.slice(offset + 42, offset + 74);
      const dataLength = parseInt(
        transactionsData.slice(offset + 74, offset + 106),
        16
      );
      const data =
        "0x" +
        transactionsData.slice(offset + 106, offset + 106 + dataLength * 2);

      transactions.push({
        operation,
        to,
        value,
        data,
      });

      offset += 106 + dataLength * 2;
    }

    console.log(`Found ${transactions.length} transactions to simulate`);

    // Simulate each individual transaction
    for (let i = 0; i < transactions.length; i++) {
      const tx = transactions[i];

      try {
        // Simulate the individual vault call
        const result = await provider.call({
          to: tx.to,
          from: safeAddress, // Call as if from Safe
          data: tx.data,
          value: tx.value || "0",
        });

        console.log(
          `Transaction ${i + 1} (${
            tx.operation === 0 ? "call" : "delegatecall"
          } to ${tx.to.slice(0, 10)}...): SUCCESS`
        );
      } catch (error: any) {
        console.log(
          `Transaction ${i + 1} (${
            tx.operation === 0 ? "call" : "delegatecall"
          } to ${tx.to.slice(0, 10)}...): FAILED - ${error.message}`
        );
        return false;
      }
    }

    console.log("Individual vault operations simulation successful!");
    return true;
  } catch (error) {
    console.log("Individual simulation failed, trying Safe execTransaction...");
    console.error("Individual simulation error:", error);
  }

  // If we get here, all simulations failed
  console.log("All simulation methods failed");
  return false;
}
