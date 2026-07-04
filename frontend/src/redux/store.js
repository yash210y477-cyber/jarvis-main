import { configureStore } from "@reduxjs/toolkit";


import aiReducer from "./slices/aiSlice";
import chatReducer from "./slices/chatSlice";
import voiceReducer from "./slices/voiceSlice";
import systemReducer from "./slices/systemSlice";
import settingsReducer from "./slices/settingsSlice";

export const store = configureStore({
  reducer: {
    ai: aiReducer,
    chat: chatReducer,
    voice: voiceReducer,
    system: systemReducer,
    settings: settingsReducer,
  },
});