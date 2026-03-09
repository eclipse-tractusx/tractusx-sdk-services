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

import * as React from "react";
import PropTypes from "prop-types";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import { useSelector } from "react-redux";
import { selectPrint } from "../managers/StateManager";

function LinearProgressWithLabel(props) {
  return (
    <Box sx={{ display: "flex", alignItems: "center" }}>
      <Box sx={{ width: "100%", mr: 1 }}>
        <LinearProgress variant="determinate" {...props} />
      </Box>
      <Box sx={{ minWidth: 35 }}>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {`${Math.round(props.value)}%`}
        </Typography>
      </Box>
    </Box>
  );
}

LinearProgressWithLabel.propTypes = {
  /**
   * The value of the progress indicator for the determinate and buffer variants.
   * Value between 0 and 100.
   */
  value: PropTypes.number.isRequired,
};

export default function LinearWithValueLabel(onProgressChange) {
  const [progress, setProgress] = React.useState(10);
  const [statusText, setStatusText] = React.useState("");
  const [statusIndex, setStatusIndex] = React.useState(0);
  const printFlags = useSelector(selectPrint);

  const statusMessages = [
    "Searching Eclipse Dataspace Connector...",
    "Finding Industry Flag Services...",
    "Retrieving Industry Flags from Service...",
    "Finalizing Results...",
    "Process Completed!",
  ];

  React.useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prevProgress) => {
        let newProgress = prevProgress >= 100 ? 10 : prevProgress + 10;
        newProgress =
          newProgress >= 90 && newProgress <= 100 && !printFlags
            ? 90
            : newProgress;
        setStatusIndex(Math.floor(newProgress / 35)); // Update the status based on progress
        return newProgress;
      });
    }, 2000);
    return () => {
      clearInterval(timer);
    };
  }, []);

  return (
    <Box sx={{ width: "100%" }}>
      <LinearProgressWithLabel value={progress} />
      <Typography
        sx={{
          mx: "auto",
          flexGrow: 0,
          fontWeight: 700,
          letterSpacing: ".1rem",
          color: "inherit",
          textDecoration: "none",
          textAlign: "center",
        }}
      >
        {statusMessages[statusIndex]}
      </Typography>
    </Box>
  );
}
