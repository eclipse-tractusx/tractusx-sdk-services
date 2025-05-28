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
import SearchView from "./views/SearchView";
import FlagListView from "./views/FlagsListView";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Loading from "./components/Loading";
import Header from "./components/Header";
import Footer from "./components/Footer";
import { useSelector, useDispatch } from "react-redux";
import Button from "@mui/material/Button";

import {
  isValidBpn,
  showFlags,
  setMessage,
  selectPrint,
  selectMessage,
  selectStatus,
  setStatus,
} from "./managers/StateManager";
import {
  BACKEND_URL,
  API_KEY,
  ENDPOINT_SEARCH_FLAGS_BY_BPN,
  ENDPOINT_GET_MY_FLAGS,
} from "./services/service.const";
import FlagService from "./services/FlagService";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

export default function MainPage() {
  const [searchValue, setSearchValue] = useState(""); // To store search value
  const [open, setOpen] = useState(true); // to close alert window
  const [companyFlags, setCompanyFlags] = useState([]);
  const printFlags = useSelector(selectPrint);
  const checkStatus = useSelector(selectStatus);
  const message = useSelector(selectMessage);
  const [isLoading, setIsLoading] = useState(false);
  const [isBpnValid, setIsBpnValid] = useState(false);
  const [isVisible, setIsVisible] = useState(true); // Initial visibility of the search component

  const dispatch = useDispatch();

  // create backend service instance to make API calls
  const flagService = new FlagService();

  // Function to handle updates from SearchView
  const getData = async (data) => {
    setSearchValue(data);

    if (data !== "") {
      let body = { bpn: data };
      setIsLoading(true);

      // if bpn is valid, then set IsBpnValid to true, else false
      if (flagService.validateBpn(data)) {
        dispatch(isValidBpn(true));
        setIsBpnValid(true);

        // Construct the url to get partner Company Flags by BPN
        const url = BACKEND_URL + ENDPOINT_SEARCH_FLAGS_BY_BPN;
        const headers = {
          "X-Api-Key": API_KEY,
          "Content-Type": "application/json",
        };
        const flagResponse = await flagService.getCompanyFlags(
          "POST",
          url,
          headers,
          body
        );

        // if the API returns the company flags
        if (flagResponse.length > 0) {
          toggleVisibility(); // hide visibility of the search component
          dispatch(showFlags(true));
          setCompanyFlags(flagResponse);
          setIsLoading(false);
          dispatch(setStatus("SUCCESS")); // set the alert title ERROR/SUCCESS
        } else {
          // if there are no company flags available
          if (flagResponse.status) dispatch(setMessage(flagResponse.message));
          else
            dispatch(setMessage("No company flags found for " + data + "..!!"));

          dispatch(setStatus("ERROR")); // set the alert title ERROR/SUCCESS
          dispatch(showFlags(false));
          setCompanyFlags([]);
          setIsLoading(false);
        }
      } else {
        // if bpn is not valid, then set to false
        dispatch(isValidBpn(false));
        setIsBpnValid(false);
        setMessage("Add a valid BPN");
        setIsLoading(false);
        dispatch(setStatus("ERROR"));
      }
    }
  };

  // Function to handle updates from HeaderComponent
  const getMenu = async (value) => {
    setSearchValue(value);
    dispatch(setMessage(""));

    // since there is no bpn based search, set the bpn validation manually as true
    dispatch(isValidBpn(true));
    setIsBpnValid(true);

    // check if "My company flags" is selected
    if (value === "My Company Flags") {
      setIsLoading(true);
      setCompanyFlags([]);
      dispatch(showFlags(false));

      // Construct the url to get my Company Flags
      const url = BACKEND_URL + ENDPOINT_GET_MY_FLAGS;
      const headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
      };
      const flagResponse = await flagService.getCompanyFlags(
        "get",
        url,
        headers
      );

      // if the API returns the company flags
      if (flagResponse.length > 0) {
        dispatch(showFlags(true));
        setCompanyFlags(flagResponse);
        setIsLoading(false);
        dispatch(setStatus("SUCCESS"));
        if (isVisible) toggleVisibility(); // hide visibility of the search component
      } else {
        // if there are no company flags available
        if (flagResponse.status) dispatch(setMessage(flagResponse.message));
        else dispatch(setMessage("No company flags found..!!"));

        dispatch(setStatus("ERROR"));
        setCompanyFlags([]);
        dispatch(showFlags(false));

        setIsLoading(false);
      }
    }
  };

  const toggleVisibility = () => {
    setIsVisible(!isVisible); // toggle search component visibility state
  };
  const handleClose = () => {
    setOpen(false); // hide the Alert when the close button is clicked
  };

  // Handle back button
  const handleBack = () => {
    setIsVisible(true); // show search component
    setCompanyFlags([]);
  };
  return (
    <Box>
      <Header onMenuChange={getMenu} />
      <Container>
        {message !== "" && open ? (
          <Box sx={{ mt: 2, maxWidth: "100%" }}>
            {checkStatus === "SUCCESS" ? (
              <Alert
                severity="success"
                action={
                  <IconButton
                    aria-label="close"
                    color="inherit"
                    size="small"
                    onClick={handleClose}
                  >
                    <CloseIcon fontSize="inherit" />
                  </IconButton>
                }
              >
                <AlertTitle>{checkStatus}</AlertTitle>
                {message}
              </Alert>
            ) : (
              <Alert
                severity="error"
                action={
                  <IconButton
                    aria-label="close"
                    color="inherit"
                    size="small"
                    onClick={handleClose}
                  >
                    <CloseIcon fontSize="inherit" />
                  </IconButton>
                }
              >
                <AlertTitle>{checkStatus}</AlertTitle>
                {message}
              </Alert>
            )}
          </Box>
        ) : null}
        <br />

        {isVisible ? (
          <SearchView onSearchChange={getData} />
        ) : (
          <Button variant="contained" onClick={handleBack}>
            Back
          </Button>
        )}
        {isLoading ? <Loading /> : null}
        {printFlags && isBpnValid ? (
          <FlagListView companyFlags={companyFlags} value={searchValue} />
        ) : null}
      </Container>
      <Footer />
    </Box>
  );
}
