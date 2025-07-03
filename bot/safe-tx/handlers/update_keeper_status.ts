import dotenv from "dotenv";
import { ethers } from "ethers";

dotenv.config();

export const updateKeeperStatus = async (
  chain_id: string,
  vault_address: string,
  provider: ethers.providers.JsonRpcProvider
) => {
  const latestBlock = await provider.getBlockNumber();
  const latestBlockTimestamp = await provider
    .getBlock(latestBlock)
    .then((block) => new Date(block.timestamp * 1000).toISOString());

  console.log(`Latest block: ${latestBlock}`);
  console.log(`Latest block timestamp: ${latestBlockTimestamp}`);

  const testUrl = `${
    process.env.API_URL
  }/lagoon/keeper_status/test/${chain_id}/${vault_address}/${latestBlock}/${encodeURIComponent(
    latestBlockTimestamp
  )}`;

  const response = await fetch(testUrl, {
    method: "POST",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to update keeper status (test endpoint): ${response.status} - ${errorText}`
    );
  }

  const result = await response.json();
  if (result.success) {
    console.log(`Keeper status (test) updated successfully: ${result.message}`);
  } else {
    throw new Error(
      `Failed to update keeper status (test endpoint): ${response.status} - ${result.error}`
    );
  }
};
