/* eslint-disable @typescript-eslint/no-explicit-any */
import { FunctionComponent, useEffect, useState } from "react";
import { getFigureData, getFileDataUrl, startListeningToParent } from "@fi-sci/figurl-interface";
import SpikeDensityPlotWidget from "./neurosift-lib/viewPlugins/Units/SpikeDensityPlot/SpikeDensityPlotWidget";
import { SetupTimeseriesSelection } from "./neurosift-lib/contexts/context-timeseries-selection";
import { useWindowDimensions } from "@fi-sci/misc";

const Figure: FunctionComponent = () => {
    useEffect(() => {
        startListening();
    }, []);

    const { data, errorMessage } = useFigureData();
    if (!data) {
        if (!errorMessage) {
            return <div>Loading...</div>;
        }
        else {
            return <div>Error: {errorMessage}</div>;
        }
    }
    if (data.type !== "multiscale_spike_density") {
        return <div>Error: Unexpected figure type: {data.type}</div>;
    }
    return (
        <FigureChild
            data={data}
        />
    )
}

type FigureChildProps = {
    data: {
        type: "multiscale_spike_density"
        uri: string
    }
}

const FigureChild: FunctionComponent<FigureChildProps> = ({ data }) => {
    const { url, errorMessage } = useFileDataUrl(data.uri);
    const { width, height } = useWindowDimensions();
    if (!url) {
        if (!errorMessage) {
            return <div>Loading file URL...</div>;
        }
        else {
            return <div>Error loading file URL: {errorMessage}</div>;
        }
    }
    return (
        <SetupTimeseriesSelection>
            <SpikeDensityPlotWidget
                width={width}
                height={height}
                multiscaleSpikeDensityOutputUrl={url}
            />
        </SetupTimeseriesSelection>
    )
}

const useFileDataUrl = (uri: string) => {
    const [url, setUrl] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    useEffect(() => {
        getFileDataUrl(uri)
            .then((url: string) => {
                setUrl(url);
            })
            .catch((err: any) => {
                setErrorMessage(`Error getting file data URL: ${err.message}`);
                console.error(`Error getting file data URL`, err);
            });
    }, [uri]);
    return { url, errorMessage };
}

const useFigureData = () => {
    const [data, setData] = useState<any>();
    const [errorMessage, setErrorMessage] = useState<string>();
    useEffect(() => {
      getFigureData()
        .then((data: any) => {
          if (!data) {
            setErrorMessage("No data in return from getFigureData()");
            return;
          }
          setData(data);
        })
        .catch((err: any) => {
          setErrorMessage(`Error getting figure data`);
          console.error(`Error getting figure data`, err);
        });
    }, []);
    return { data, errorMessage };
  };

let listeningToParent = false;
const startListening = () => {
    if (listeningToParent) {
        return;
    }
    startListeningToParent();
    listeningToParent = true;
}

export default Figure;