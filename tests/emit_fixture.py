"""A miniature but structurally faithful EMIT L2A granule.

Same groups, same variable names, the same geometry lookup table with its
fill value, and the same 285-band wavelength axis as the real product - small
enough to build in a second. It exists so the hyperspectral branch of the
notebook is executed by the test suite, not only its skip branch.
"""
import numpy as np, xarray as xr, os

# The AOI the notebook uses, so fields land inside the swath.
AOI = [38.15, 29.75, 38.85, 30.30]
WL  = np.linspace(380.9, 2492.8, 285).astype("float32")

def write(path, downtrack=120, crosstrack=90, ortho=560):
    rng = np.random.default_rng(4242)

    # reflectance cube, (downtrack, crosstrack, bands)
    refl = (0.05 + 0.25 * rng.random((downtrack, crosstrack, 285))).astype("float32")
    # a red edge, so REP and the 970 nm depth are not pure noise
    refl[:, :, WL > 750] += 0.25
    refl[:, :, (WL > 950) & (WL < 990)] -= 0.06

    # geometry lookup table over the ortho grid, 1-based, 0 = no data.
    gx = rng.integers(1, crosstrack + 1, size=(ortho, ortho)).astype("float32")
    gy = rng.integers(1, downtrack + 1, size=(ortho, ortho)).astype("float32")
    # the real product carries a fill value here, which is what forces these
    # arrays to float and breaks naive indexing - keep that property.
    holes = rng.random((ortho, ortho)) < 0.25
    gx[holes] = np.nan
    gy[holes] = np.nan

    lon0, lat0 = AOI[0], AOI[3]
    dlon = (AOI[2] - AOI[0]) / ortho
    dlat = (AOI[3] - AOI[1]) / ortho
    geotransform = [lon0, dlon, 0.0, lat0, 0.0, -dlat]

    root = xr.Dataset(
        {"reflectance": (("downtrack", "crosstrack", "bands"), refl)},
        attrs={"geotransform": geotransform},
    )
    band = xr.Dataset({"wavelengths": (("bands",), WL)})
    loc  = xr.Dataset({"glt_x": (("ortho_y", "ortho_x"), gx),
                       "glt_y": (("ortho_y", "ortho_x"), gy)})

    if os.path.exists(path):
        os.remove(path)
    root.to_netcdf(path, engine="h5netcdf", mode="w")
    band.to_netcdf(path, engine="h5netcdf", mode="a", group="sensor_band_parameters")
    loc.to_netcdf(path, engine="h5netcdf", mode="a", group="location")
    return path

if __name__ == "__main__":
    p = write("emit_fixture.nc")
    print(p, "%.1f KB" % (os.path.getsize(p) / 1024))
    print("root:", list(xr.open_dataset(p).data_vars),
          "| geotransform:", xr.open_dataset(p).attrs["geotransform"])
    print("bands:", xr.open_dataset(p, group="sensor_band_parameters").wavelengths.shape)
    print("location:", list(xr.open_dataset(p, group="location").data_vars))
