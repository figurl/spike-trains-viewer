import os
import tempfile
import numpy as np
import lindi
import kachery as ka


def prepare_multiscale_spike_density_from_nwb_units_table(
    *, nwb_url: str, units_path: str, bin_size_msec: float, kachery_zone: str
):
    os.environ["KACHERY_ZONE"] = kachery_zone
    if nwb_url.endswith(".lindi.json") or nwb_url.endswith(".lindi.tar"):
        f = lindi.LindiH5pyFile.from_lindi_file(nwb_url)
    else:
        f = lindi.LindiH5pyFile.from_hdf5_file(nwb_url)

    units_group = f[units_path]
    assert isinstance(units_group, lindi.LindiH5pyGroup)

    spike_times = units_group["spike_times"][()]
    spike_times_index = units_group["spike_times_index"][()]
    spike_trains = []
    offset = 0
    for i in range(len(spike_times_index)):
        st = spike_times[offset:int(spike_times_index[i])]
        # exclude the NaN from the spike times
        st = st[~np.isnan(st)]
        spike_trains.append(st)
        offset = int(spike_times_index[i])
    num_units = len(spike_trains)

    f.close()

    start_time_sec = float(0)  # we assume we are starting at time 0
    # end time is the max over all the spike trains
    all_spike_times = np.concatenate(spike_trains)
    end_time_sec = float(np.max(all_spike_times))

    print(f"Start time: {start_time_sec}")
    print(f"End time: {end_time_sec}")

    firing_rates_hz = [len(st) / (end_time_sec - start_time_sec) for st in spike_trains]

    print(f"Number of units: {num_units}")
    print(f"Total number of spikes: {sum([len(st) for st in spike_trains])}")
    for i in range(num_units):
        print(f"Unit {i}: {len(spike_trains[i])} spikes, {firing_rates_hz[i]:.2f} Hz")

    bin_size_sec = bin_size_msec / 1000
    num_bins = int((end_time_sec - start_time_sec) / bin_size_sec)
    print(f"Number of bins: {num_bins}")

    # bin the spikes
    spike_counts = np.zeros((num_bins, num_units), dtype=np.int32)
    for i in range(num_units):
        spike_counts[:, i], _ = np.histogram(
            spike_trains[i], bins=num_bins, range=(start_time_sec, end_time_sec)
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_fname = f"{tmpdir}/output.lindi.tar"
        g = lindi.LindiH5pyFile.from_lindi_file(output_fname, mode="w")

        num_bins_per_chunk = 5_000_000 // num_units

        ds = g.create_dataset(
            "spike_counts",
            data=spike_counts,
            chunks=(np.minimum(num_bins_per_chunk, num_bins), num_units),
            compression='zlib'  # use zlib to be deterministic
        )
        ds.attrs["bin_size_sec"] = bin_size_sec
        ds.attrs["start_time_sec"] = start_time_sec
        ds_factor = 1
        while num_bins // ds_factor > 10000:
            rel_ds_factor = 3
            print(f"Downsampling by {ds_factor * rel_ds_factor}")
            num_ds_bins = spike_counts.shape[0] // rel_ds_factor
            X = spike_counts[: num_ds_bins * rel_ds_factor, :].reshape(
                num_ds_bins, rel_ds_factor, num_units
            )
            spike_counts_ds = np.sum(X, axis=1).reshape(num_ds_bins, num_units)
            ds_factor = ds_factor * rel_ds_factor
            ds0 = g.create_dataset(
                f"spike_counts_ds_{ds_factor}",
                data=spike_counts_ds.astype(np.int32),
                chunks=(np.minimum(num_bins_per_chunk, num_ds_bins), num_units),
                compression='zlib'  # use zlib to be deterministic
            )
            ds0.attrs["bin_size_sec"] = bin_size_sec * ds_factor
            ds0.attrs["start_time_sec"] = start_time_sec
            spike_counts = spike_counts_ds

        g.close()

        file_size = os.path.getsize(output_fname)
        file_size_mb = file_size / 1e6
        print(f"Uploading to kachery ({file_size_mb} MB)")
        uri = ka.store_file(
            output_fname, label="multiscale_spike_density.lindi.tar", uri_type=2
        )
        uri2 = ka.store_json({
            'type': 'multiscale_spike_density',
            'uri': uri
        })
        return uri2


if __name__ == "__main__":
    # https://neurosift.app/?p=/nwb&url=https://api.dandiarchive.org/api/assets/309f7aaf-e821-409c-afa5-d2db0b109b06/download/&dandisetId=000473&dandisetVersion=0.230417.1502
    nwb_url = "https://api.dandiarchive.org/api/assets/309f7aaf-e821-409c-afa5-d2db0b109b06/download/"
    units_path = "/units"
    bin_size_msec = 20
    kachery_zone = "scratch"
    uri = prepare_multiscale_spike_density_from_nwb_units_table(
        nwb_url=nwb_url,
        units_path=units_path,
        bin_size_msec=bin_size_msec,
        kachery_zone=kachery_zone,
    )
    print(f"URI: {uri}")
