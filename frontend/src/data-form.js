import { useState, useEffect } from "react";
import { Box, TextField, Button } from "@mui/material";
import axios from "axios";

const endpointMapping = {
  Notion: "notion",
  Airtable: "airtable",
  Hubspot: "hubspot",
};

export const DataForm = ({ integrationType, credentials }) => {
  const [loadedData, setLoadedData] = useState(null);
  const endpoint = endpointMapping[integrationType];

  async function handleLoad() {
    try {
      const formData = new FormData();
      formData.append("credentials", JSON.stringify(credentials));
      const response = await axios.post(
        `http://localhost:8000/integrations/${endpoint}/load`,
        formData
      );
      const data = response.data;
      setLoadedData(data);
    } catch (e) {
      alert(e?.response?.data?.detail);
    }
  }

  // useEffect(() => {
  //   // Log loadedData whenever it changes
  //   if (loadedData !== null) {
  //     console.log("Loaded Data Updated:", loadedData);
  //   }
  // }, [loadedData]);

  return (
    <Box justifyContent="center" alignItems="center" width="450px">
      <Box display="flex" flexDirection="column">
        <TextField
          label="Loaded Data"
          // color="black"
          value={loadedData ? JSON.stringify(loadedData, null, 2) : ""}
          sx={{ mt: 2 }}
          InputLabelProps={{ shrink: true }}
          multiline
          minRows={2}
          disabled
        />
        <Button onClick={handleLoad} sx={{ mt: 2 }} variant="contained">
          Load Data
        </Button>
        <Button
          onClick={() => setLoadedData(null)}
          sx={{ mt: 1 }}
          variant="contained"
        >
          Clear Data
        </Button>
      </Box>
    </Box>
  );
};
