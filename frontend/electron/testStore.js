import { searchStoreApp } from "./appsFolderSearch.js";

async function test() {
  console.log("Testing WhatsApp...");

  const result = await searchStoreApp("WhatsApp");

  console.log(result);
}

test();