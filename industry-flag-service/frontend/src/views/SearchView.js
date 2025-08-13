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

import React, { useState } from "react";
import { Container } from "@mui/material";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import SearchIcon from "@mui/icons-material/Search";
import FlagService from "../services/FlagService";
import { useDispatch } from "react-redux";
import {
  isValidBpn,
  showFlags,
  setMessage,
  setStatus,
} from "../managers/StateManager";

export default function SearchView({ onSearchChange }) {
  // State for search input and data to be displayed
  const [searchTerm, setSearchTerm] = useState("");
  const dispatch = useDispatch();

  // create flag service instance to make validate BPN
  const flagService = new FlagService();

  const handleChange = (event) => {
    setSearchTerm(event.target.value);
  };

  const handleSearch = () => {
    onSearchChange(searchTerm);

    if (flagService.validateBpn(searchTerm)) {
      // Valid BPN
      dispatch(setMessage(""));
      dispatch(isValidBpn(true));
      dispatch(showFlags(true));
    } else {
      // Invalid BPN
      dispatch(setMessage("Add a valid BPN number"));
      dispatch(setStatus("ERROR"));
      dispatch(isValidBpn(false));
      dispatch(showFlags(false));
    }
  };
  return (
    <Container>
      <Box sx={{ mx: "auto", mt: 5, width: 300, maxWidth: "100%" }}>
        <TextField
          fullWidth
          onChange={handleChange}
          label="Business Partner Number"
          id="bpnText"
        />
      </Box>
      <Box
        sx={{
          mx: "auto",
          width: 300,
          "& button": { mt: 2, mb: 5 },
          maxWidth: "100%",
        }}
      >
        <Button
          fullWidth
          variant="contained"
          onClick={handleSearch}
          startIcon={<SearchIcon />}
        >
          Search
        </Button>
      </Box>
    </Container>
  );
}
