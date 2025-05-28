/*
  Tractus-X - Industry Flag Service

  Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
  Copyright (c) 2025 Contributors to the Eclipse Foundation

  See the NOTICE file(s) distributed with this work for additional
  information regarding copyright ownership.

  This program and the accompanying materials are made available under the
  terms of the Apache License, Version 2.0 which is available at
  https://www.apache.org/licenses/LICENSE-2.0.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the
  License for the specific language govern in permissions and limitations
  under the License.

  SPDX-License-Identifier: Apache-2.0
*/

import { createSlice } from "@reduxjs/toolkit";

export const stateManager = createSlice({
  name: "manager",
  initialState: {
    showFlags: false,
    validateBpn: false,
    message: "",
    status: "",
  },
  reducers: {
    // state to display the list of flags
    showFlags: (state, action) => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes.
      // Also, no return statement is required from these functions.
      state.showFlags = action.payload;
    },
    // state to validate the BPN
    isValidBpn: (state, action) => {
      state.validateBpn = action.payload;
    },
    // status to set the Error or success state
    setStatus: (state, action) => {
      state.status = action.payload;
    },
    // The message to display
    setMessage: (state, action) => {
      state.message = action.payload;
    },
  },
});

// Action creators are generated for each case reducer function
export const { isValidBpn, showFlags, setMessage, setStatus } =
  stateManager.actions;
export const selectMessage = (state) => state.manager.message;
export const selectPrint = (state) => state.manager.showFlags;
export const selectStatus = (state) => state.manager.status;
export const selectValidBpn = (state) => state.manager.validateBpn;

export default stateManager.reducer;
