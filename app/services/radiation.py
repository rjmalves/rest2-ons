from typing import Union

import numpy as np
import polars as pl
from scipy.optimize import minimize  # type: ignore[import-untyped]

from app.readers import LocationInputData
from app.utils.metrics import mae, me, rmse
from app.utils.utils import extraterrestrial_radiation

ArrayLike = Union[np.ndarray, float, int]


class AirMassResults:
    def __init__(
        self,
        rayleigh_scattering: np.ndarray,
        rayleigh_scattering_scaled: np.ndarray,
        ozone_absorption: np.ndarray,
        water_vapour_absorption: np.ndarray,
        aerosol_extinction: np.ndarray,
        angstrom_turbidity: np.ndarray,
    ):
        self.rayleigh_scattering = rayleigh_scattering
        self.rayleigh_scattering_scaled = rayleigh_scattering_scaled
        self.ozone_absorption = ozone_absorption
        self.water_vapour_absorption = water_vapour_absorption
        self.aerosol_extinction = aerosol_extinction
        self.angstrom_turbidity = angstrom_turbidity


class BandRadiationResults:
    def __init__(
        self,
        TR: ArrayLike,
        Tg: ArrayLike,
        To: ArrayLike,
        Tn: ArrayLike,
        Tw: ArrayLike,
        TA: ArrayLike,
        Tn166: ArrayLike,
        Tw166: ArrayLike,
        BR: ArrayLike,
        F: ArrayLike,
        TAS: ArrayLike,
        rs: ArrayLike,
        Ba: ArrayLike | None = None,
    ):
        self.TR = TR
        self.Tg = Tg
        self.To = To
        self.Tn = Tn
        self.Tw = Tw
        self.TA = TA
        self.Tn166 = Tn166
        self.Tw166 = Tw166
        self.BR = BR
        self.F = F
        self.TAS = TAS
        self.rs = rs
        self.Ba = Ba


class BandIrradianceResults:
    def __init__(
        self,
        direct_beam: np.ndarray,
        diffuse_on_absorbing_ground: np.ndarray,
        multiple_reflections: np.ndarray,
    ):
        self.direct_beam = direct_beam
        self.diffuse_on_absorbing_ground = diffuse_on_absorbing_ground
        self.multiple_reflections = multiple_reflections


class CloudTransmittanceResults:
    def __init__(
        self,
        direct: np.ndarray,
        diffuse: np.ndarray,
    ):
        self.direct = direct
        self.diffuse = diffuse


class REST2Result:
    def __init__(
        self,
        ghi: pl.DataFrame,
        ghi_tracker: pl.DataFrame,
        dni: pl.DataFrame,
        dhi: pl.DataFrame,
        ghi_cs: pl.DataFrame,
        ghi_tracker_cs: pl.DataFrame,
        dni_cs: pl.DataFrame,
        dhi_cs: pl.DataFrame,
    ):
        self.ghi = ghi
        self.ghi_tracker = ghi_tracker
        self.dni = dni
        self.dhi = dhi
        self.ghi_cs = ghi_cs
        self.ghi_tracker_cs = ghi_tracker_cs
        self.dni_cs = dni_cs
        self.dhi_cs = dhi_cs

    def get(self, radiation_type: str) -> pl.DataFrame:
        if radiation_type == "ghi":
            return self.ghi
        elif radiation_type == "dni":
            return self.dni
        elif radiation_type == "dhi":
            return self.dhi
        if radiation_type == "ghi_tracker":
            return self.ghi_tracker
        else:
            raise ValueError(f"Unknown radiation type: {radiation_type}")


class REST2:
    ANGSTROM_EXPONENT_BOUNDS = [0.0, 2.5]
    SURFACE_PRESSURE_BOUNDS = [300.0, 1100.0]
    WATER_VAPOUR_BOUNDS = [0.0, 10.0]
    OZONE_BOUNDS = [0.0, 10.0]
    NITROGEN_DIOXIDE_BOUNDS = [0.0, 0.03]
    SURFACE_ALBEDO_BOUNDS = [0.0, 1.0]
    COD_BOUNDS = [0.0, 160.0]

    DEFAULT_PARAMETERS = {"mu0": 0.0, "g": 0.85}

    # Instance attributes (typed as they are after __init__ completes)
    cod: np.ndarray
    surface_albedo: np.ndarray
    angstrom_exponent: np.ndarray
    pressure: np.ndarray
    water_vapour: np.ndarray
    ozone: np.ndarray
    nitrogen_dioxide: np.ndarray
    optical_depth_550nm: np.ndarray
    lat: float
    lon: float
    extraterrestrial_radiation: np.ndarray
    zenith_angle: np.ndarray
    time_steps: pl.Series

    def __init__(self, location_data: LocationInputData):
        # Start with DataFrames
        _cod = location_data.cod
        _surface_albedo = location_data.albedo
        _angstrom_exponent = location_data.angstrom_exponent
        _pressure = location_data.psurf
        _water_vapour = location_data.h2o
        _ozone = location_data.o3
        _nitrogen_dioxide = location_data.no2
        _optical_depth_550nm = location_data.od550
        self.lat = location_data.latitude
        self.lon = location_data.longitude

        # Generate solar data
        self.extraterrestrial_radiation, self.zenith_angle = (
            extraterrestrial_radiation(
                _cod["time"].to_numpy(), self.lat, self.lon
            )
        )

        # Apply variable bounds
        if _angstrom_exponent is None:
            raise ValueError("angstrom_exponent must not be None")
        _angstrom_exponent = _angstrom_exponent.with_columns(
            pl.col("valor").clip(*self.ANGSTROM_EXPONENT_BOUNDS)
        )
        _pressure = _pressure.with_columns(
            pl.col("valor").clip(*self.SURFACE_PRESSURE_BOUNDS)
        )
        _water_vapour = _water_vapour.with_columns(
            pl.col("valor").clip(*self.WATER_VAPOUR_BOUNDS)
        )
        _ozone = _ozone.with_columns(pl.col("valor").clip(*self.OZONE_BOUNDS))
        _nitrogen_dioxide = _nitrogen_dioxide.with_columns(
            pl.col("valor").clip(*self.NITROGEN_DIOXIDE_BOUNDS)
        )
        _surface_albedo = _surface_albedo.with_columns(
            pl.col("valor").clip(*self.SURFACE_ALBEDO_BOUNDS)
        )
        _cod = _cod.with_columns(pl.col("valor").clip(*self.COD_BOUNDS))

        # Prepare variables - convert to numpy arrays
        self.angstrom_exponent = self._prepare_variable(_angstrom_exponent)
        self.pressure = self._prepare_variable(_pressure)
        self.water_vapour = self._prepare_variable(_water_vapour)
        self.ozone = self._prepare_variable(_ozone)
        self.nitrogen_dioxide = self._prepare_variable(_nitrogen_dioxide)
        self.surface_albedo = self._prepare_variable(_surface_albedo)
        self.optical_depth_550nm = self._prepare_variable(_optical_depth_550nm)
        self.time_steps = _cod.sort("time")["time"]
        self.cod = np.nan_to_num(self._prepare_variable(_cod))

    def _prepare_variable(
        self,
        variable: pl.DataFrame,
    ) -> np.ndarray:
        variable = variable.sort("time")
        return variable["valor"].to_numpy()

    def _postprocess_variable(self, variable: np.ndarray) -> pl.DataFrame:
        return pl.DataFrame({"time": self.time_steps, "valor": variable})

    def _postprocess_variables(
        self,
        ghi: np.ndarray,
        ghi_tracker: np.ndarray,
        dni: np.ndarray,
        dhi: np.ndarray,
        ghi_cs: np.ndarray,
        ghi_tracker_cs: np.ndarray,
        dni_cs: np.ndarray,
        dhi_cs: np.ndarray,
    ) -> REST2Result:
        ghi_df = self._postprocess_variable(ghi)
        ghi_tracker_df = self._postprocess_variable(ghi_tracker)
        dni_df = self._postprocess_variable(dni)
        dhi_df = self._postprocess_variable(dhi)
        ghi_cs_df = self._postprocess_variable(ghi_cs)
        ghi_tracker_cs_df = self._postprocess_variable(ghi_tracker_cs)
        dni_cs_df = self._postprocess_variable(dni_cs)
        dhi_cs_df = self._postprocess_variable(dhi_cs)

        return REST2Result(
            ghi_df,
            ghi_tracker_df,
            dni_df,
            dhi_df,
            ghi_cs_df,
            ghi_tracker_cs_df,
            dni_cs_df,
            dhi_cs_df,
        )

    def _evaluate_air_masses(
        self,
        zenith_angle: np.ndarray,
        angstrom_exponent: np.ndarray,
        pressure: np.ndarray,
        optical_depth_550nm: np.ndarray,
    ) -> AirMassResults:
        # air mass for aerosols extinction
        # complex_temp = np.array(zenith_angle * 180. / np.pi, dtype=np.complex)
        complex_temp = np.array(zenith_angle * 180.0 / np.pi, dtype=complex)

        ama = np.abs(
            np.power(
                np.cos(zenith_angle)
                + 0.16851
                * np.power(complex_temp, 0.18198)
                / np.power(95.318 - complex_temp, 1.9542),
                -1,
            )
        )
        # air mass for water vapor absorption
        amw = np.abs(
            np.power(
                np.cos(zenith_angle)
                + 0.10648
                * np.power(complex_temp, 0.11423)
                / np.power(93.781 - complex_temp, 1.9203),
                -1,
            )
        )
        # air mass for nitrogen dioxide absorption
        # amn = np.abs(np.power(np.cos(zenith_angle) + 1.1212 * np.power(zenith_angle * 180. / np.pi, 1.6132) / np.power(
        #   3.2629 - zenith_angle * 180. / np.pi, 1.9203), -1))
        # air mass for ozone absorption
        amo = np.abs(
            np.power(
                np.cos(zenith_angle)
                + 1.0651
                * np.power(complex_temp, 0.6379)
                / np.power(101.8 - complex_temp, 2.2694),
                -1,
            )
        )
        # air mass for Rayleigh scattering and uniformly mixed gases absorption
        amR = np.abs(
            np.power(
                np.cos(zenith_angle)
                + 0.48353
                * np.power(complex_temp, 0.095846)
                / np.power(96.741 - complex_temp, 1.754),
                -1,
            )
        )
        amRe = np.abs(
            (pressure / 1013.25)
            * np.power(
                np.cos(zenith_angle)
                + 0.48353
                * (np.power(complex_temp, 0.095846))
                / np.power(96.741 - complex_temp, 1.754),
                -1,
            )
        )

        # Angstrom turbidity
        ang_beta = optical_depth_550nm / np.power(0.55, -1 * angstrom_exponent)
        ang_beta[ang_beta > 1.1] = 1.1
        ang_beta[ang_beta < 0] = 0

        return AirMassResults(
            rayleigh_scattering=amR,
            rayleigh_scattering_scaled=amRe,
            ozone_absorption=amo,
            aerosol_extinction=ama,
            water_vapour_absorption=amw,
            angstrom_turbidity=ang_beta,
        )

    def _band_1_radiation(
        self,
        ozone: np.ndarray,
        nitrogen_dioxide: np.ndarray,
        water_vapour: np.ndarray,
        angstrom_exponent: np.ndarray,
        zenith_angle: np.ndarray,
        air_masses: AirMassResults,
    ) -> BandRadiationResults:
        amR = air_masses.rayleigh_scattering
        amRe = air_masses.rayleigh_scattering_scaled
        amo = air_masses.ozone_absorption
        amw = air_masses.water_vapour_absorption
        ama = air_masses.aerosol_extinction
        AB1 = air_masses.angstrom_turbidity
        alph1 = angstrom_exponent

        # transmittance for Rayleigh scattering
        TR1 = (1 + 1.8169 * amRe - 0.033454 * np.power(amRe, 2)) / (
            1 + 2.063 * amRe + 0.31978 * np.power(amRe, 2)
        )

        # transmittance for uniformly mixed gases absorption
        Tg1 = (1 + 0.95885 * amRe + 0.012871 * np.power(amRe, 2)) / (
            1 + 0.96321 * amRe + 0.015455 * np.power(amRe, 2)
        )

        # transmittance for Ozone absorption
        f1 = (
            ozone
            * (10.979 - 8.5421 * ozone)
            / (1 + 2.0115 * ozone + 40.189 * np.power(ozone, 2))
        )
        f2 = (
            ozone
            * (-0.027589 - 0.005138 * ozone)
            / (1 - 2.4857 * ozone + 13.942 * np.power(ozone, 2))
        )
        f3 = (
            ozone
            * (10.995 - 5.5001 * ozone)
            / (1 + 1.6784 * ozone + 42.406 * np.power(ozone, 2))
        )
        To1 = (1 + f1 * amo + f2 * np.power(amo, 2)) / (1 + f3 * amo)

        # transmittance for Nitrogen dioxide absorption
        un = nitrogen_dioxide
        g1 = (0.17499 + 41.654 * un - 2146.4 * np.power(un, 2)) / (
            1 + 22295.0 * np.power(un, 2)
        )
        g2 = un * (-1.2134 + 59.324 * un) / (1 + 8847.8 * np.power(un, 2))
        g3 = (0.17499 + 61.658 * un + 9196.4 * np.power(un, 2)) / (
            1 + 74109.0 * np.power(un, 2)
        )
        Tn1_middle = (1 + g1 * amw + g2 * np.power(amw, 2)) / (1 + g3 * amw)
        Tn1_middle[Tn1_middle > 1] = 1
        Tn1 = Tn1_middle
        # Tn1 = min(1, ((1 + g1 * amw + g2 * np.power(amw, 2)) / (1 + g3 * amw)))
        Tn1166_middle = (1 + g1 * 1.66 + g2 * np.power(1.66, 2)) / (
            1 + g3 * 1.66
        )
        Tn1166_middle[Tn1166_middle > 1] = 1
        Tn1166 = Tn1166_middle
        # Tn1166 = min(1, ((1 + g1 * 1.66 + g2 * np.power(1.66, 2)) / (1 + g3 * 1.66)))  # atairmass = 1.66
        # transmittance for Water Vapor absorption
        h1 = (
            water_vapour
            * (0.065445 + 0.00029901 * water_vapour)
            / (1 + 1.2728 * water_vapour)
        )
        h2 = (
            water_vapour
            * (0.065687 + 0.0013218 * water_vapour)
            / (1 + 1.2008 * water_vapour)
        )
        Tw1 = (1 + h1 * amw) / (1 + h2 * amw)
        Tw1166 = (1 + h1 * 1.66) / (1 + h2 * 1.66)  # atairmass = 1.66

        # coefficients of angstrom_alpha

        d0 = 0.57664 - 0.024743 * alph1
        d1 = (0.093942 - 0.2269 * alph1 + 0.12848 * np.power(alph1, 2)) / (
            1 + 0.6418 * alph1
        )
        d2 = (-0.093819 + 0.36668 * alph1 - 0.12775 * np.power(alph1, 2)) / (
            1 - 0.11651 * alph1
        )
        d3 = (
            alph1
            * (0.15232 - 0.087214 * alph1 + 0.012664 * np.power(alph1, 2))
            / (1 - 0.90454 * alph1 + 0.26167 * np.power(alph1, 2))
        )
        ua1 = np.log(1 + ama * AB1)
        lam1 = (d0 + d1 * ua1 + d2 * np.power(ua1, 2)) / (
            1 + d3 * np.power(ua1, 2)
        )

        # Aeroso transmittance
        ta1 = np.abs(AB1 * np.power(lam1, -1 * alph1))
        TA1 = np.exp(-ama * ta1)

        # Aeroso scattering transmittance
        TAS1 = np.exp(-ama * 0.92 * ta1)  # w1 = 0.92recommended

        # forward scattering fractions for Rayleigh extinction
        BR1 = 0.5 * (0.89013 - 0.0049558 * amR + 0.000045721 * np.power(amR, 2))
        # the aerosol forward scatterance factor
        Ba = 1 - np.exp(-0.6931 - 1.8326 * np.cos(zenith_angle))

        # Aerosol scattering correction factor
        g0 = (3.715 + 0.368 * ama + 0.036294 * np.power(ama, 2)) / (
            1 + 0.0009391 * np.power(ama, 2)
        )
        g1 = (-0.164 - 0.72567 * ama + 0.20701 * np.power(ama, 2)) / (
            1 + 0.0019012 * np.power(ama, 2)
        )
        g2 = (-0.052288 + 0.31902 * ama + 0.17871 * np.power(ama, 2)) / (
            1 + 0.0069592 * np.power(ama, 2)
        )
        F1 = (g0 + g1 * ta1) / (1 + g2 * ta1)

        # sky albedo
        rs1 = (
            0.13363
            + 0.00077358 * alph1
            + AB1 * (0.37567 + 0.22946 * alph1) / (1 - 0.10832 * alph1)
        ) / (1 + AB1 * (0.84057 + 0.68683 * alph1) / (1 - 0.08158 * alph1))

        return BandRadiationResults(
            TR=TR1,
            Tg=Tg1,
            To=To1,
            Tn=Tn1,
            Tw=Tw1,
            TA=TA1,
            Tn166=Tn1166,
            Tw166=Tw1166,
            BR=BR1,
            F=F1,
            TAS=TAS1,
            rs=rs1,
            Ba=Ba,
        )

    def _band_2_radiation(
        self,
        water_vapour: np.ndarray,
        angstrom_exponent: np.ndarray,
        zenith_angle: np.ndarray,
        air_masses: AirMassResults,
    ) -> BandRadiationResults:
        amRe = air_masses.rayleigh_scattering_scaled
        amw = air_masses.water_vapour_absorption
        ama = air_masses.aerosol_extinction
        AB2 = air_masses.angstrom_turbidity
        alph2 = angstrom_exponent

        # transmittance for Rayleigh scattering
        TR2 = (1 - 0.010394 * amRe) / (1 - 0.00011042 * np.power(amRe, 2))
        # transmittance for uniformly mixed gases absorption
        Tg2 = (1 + 0.27284 * amRe - 0.00063699 * np.power(amRe, 2)) / (
            1 + 0.30306 * amRe
        )
        # transmittance for Ozone absorption
        To2 = 1  # Ozone (none)
        # transmittance for Nitrogen dioxide absorption
        Tn2 = 1  # Nitrogen (none)
        Tn2166 = 1  # at air mass=1.66

        # transmittance for water vapor  absorption
        c1 = (
            water_vapour
            * (
                19.566
                - 1.6506 * water_vapour
                + 1.0672 * np.power(water_vapour, 2)
            )
            / (1 + 5.4248 * water_vapour + 1.6005 * np.power(water_vapour, 2))
        )
        c2 = (
            water_vapour
            * (
                0.50158
                - 0.14732 * water_vapour
                + 0.047584 * np.power(water_vapour, 2)
            )
            / (1 + 1.1811 * water_vapour + 1.0699 * np.power(water_vapour, 2))
        )
        c3 = (
            water_vapour
            * (
                21.286
                - 0.39232 * water_vapour
                + 1.2692 * np.power(water_vapour, 2)
            )
            / (1 + 4.8318 * water_vapour + 1.412 * np.power(water_vapour, 2))
        )
        c4 = (
            water_vapour
            * (
                0.70992
                - 0.23155 * water_vapour
                + 0.096514 * np.power(water_vapour, 2)
            )
            / (1 + 0.44907 * water_vapour + 0.75425 * np.power(water_vapour, 2))
        )
        Tw2 = (1 + c1 * amw + c2 * np.power(amw, 2)) / (
            1 + c3 * amw + c4 * np.power(amw, 2)
        )
        Tw2166 = (1 + c1 * 1.66 + c2 * np.power(1.66, 2)) / (
            1 + c3 * 1.66 + c4 * np.power(1.66, 2)
        )

        # coefficients of angstrom_alpha
        e0 = (1.183 - 0.022989 * alph2 + 0.020829 * np.power(alph2, 2)) / (
            1 + 0.11133 * alph2
        )
        e1 = (-0.50003 - 0.18329 * alph2 + 0.23835 * np.power(alph2, 2)) / (
            1 + 1.6756 * alph2
        )
        e2 = (-0.50001 + 1.1414 * alph2 + 0.0083589 * np.power(alph2, 2)) / (
            1 + 11.168 * alph2
        )
        e3 = (-0.70003 - 0.73587 * alph2 + 0.51509 * np.power(alph2, 2)) / (
            1 + 4.7665 * alph2
        )
        ua2 = np.log(1 + ama * AB2)
        lam2 = (e0 + e1 * ua2 + e2 * np.power(ua2, 2)) / (1 + e3 * ua2)

        # Aerosol transmittance
        lam2_temp = np.array(lam2, dtype=complex)
        ta2 = np.abs(AB2 * np.power(lam2_temp, -alph2))
        TA2 = np.exp(-1 * ama * ta2)
        TAS2 = np.exp(-1 * ama * 0.84 * ta2)  # w2=0.84 recommended

        # forward scattering fractions for Rayleigh extinction
        BR2 = 0.5  # multi scatter negibile in Band 2
        # the aerosol forward scatterance factor
        Ba = 1 - np.exp(-0.6931 - 1.8326 * np.cos(zenith_angle))

        # Aerosol scattering correction
        h0 = (3.4352 + 0.65267 * ama + 0.00034328 * np.power(ama, 2)) / (
            1 + 0.034388 * np.power(ama, 1.5)
        )
        h1 = (1.231 - 1.63853 * ama + 0.20667 * np.power(ama, 2)) / (
            1 + 0.1451 * np.power(ama, 1.5)
        )
        h2 = (0.8889 - 0.55063 * ama + 0.50152 * np.power(ama, 2)) / (
            1 + 0.14865 * np.power(ama, 1.5)
        )
        F2 = (h0 + h1 * ta2) / (1 + h2 * ta2)

        # sky albedo
        rs2 = (
            0.010191
            + 0.00085547 * alph2
            + AB2 * (0.14618 + 0.062758 * alph2) / (1 - 0.19402 * alph2)
        ) / (1 + AB2 * (0.58101 + 0.17426 * alph2) / (1 - 0.17586 * alph2))

        return BandRadiationResults(
            TR=TR2,
            Tg=Tg2,
            To=To2,
            Tn=Tn2,
            Tw=Tw2,
            TA=TA2,
            Tn166=Tn2166,
            Tw166=Tw2166,
            BR=BR2,
            F=F2,
            TAS=TAS2,
            rs=rs2,
            Ba=Ba,
        )

    def _cloud_transmittance(
        self, cod: np.ndarray, mu0: float, g: float
    ) -> CloudTransmittanceResults:
        # Cloud Transmittance -> TC Band 1 = TC Band 2, assuming the cloud as a grey/white body
        # g = 0.85  #  For liquid water clouds, scattering is mostly in the forward direction, with g≃0.85, whereas for ice clouds g≃0.7 - https://amt.copernicus.org/articles/16/4975/2023/#bib1.bibx53
        direct_transmittance = np.exp(
            -1 * cod / (0.5 + mu0)
        )  # Pg 412 (Direct and Diffuse Transmittance) - Livro Petty, 2006
        diffuse_transmittance = 1 / (1 + ((1 - g) * cod)) - np.exp(
            -1 * cod / (0.5 + mu0)
        )  # Pg 412 (Direct and Diffuse Transmittance) - Livro Petty, 2006
        return CloudTransmittanceResults(
            direct=direct_transmittance, diffuse=diffuse_transmittance
        )

    def _band_1_irradiance(
        self,
        extraterrestrial_radiation: np.ndarray,
        zenith_angle: np.ndarray,
        surface_albedo: np.ndarray,
        radiation: BandRadiationResults,
        transmittance: CloudTransmittanceResults,
    ) -> tuple[BandIrradianceResults, BandIrradianceResults]:
        TR1 = radiation.TR
        Tg1 = radiation.Tg
        To1 = radiation.To
        Tn1 = radiation.Tn
        Tw1 = radiation.Tw
        TA1 = radiation.TA
        Tn1166 = radiation.Tn166
        Tw1166 = radiation.Tw166
        BR1 = radiation.BR
        F1 = radiation.F
        TAS1 = radiation.TAS
        rs1 = radiation.rs
        rg = surface_albedo
        Ba = radiation.Ba
        if Ba is None:
            raise ValueError(
                "Ba must not be None for band 1 irradiance calculation"
            )
        TC_dir = transmittance.direct
        TC_dif = transmittance.diffuse

        E0n1 = extraterrestrial_radiation * 0.46512
        # direct beam irradiance
        Ebn1 = E0n1 * TR1 * Tg1 * To1 * Tn1 * Tw1 * TA1
        Ebn1_cloud = Ebn1 * TC_dir
        # the incident diffuse irradiance on a perfectly absorbing ground
        Edp1 = (
            E0n1
            * np.cos(zenith_angle)
            * To1
            * Tg1
            * Tn1166
            * Tw1166
            * (
                BR1 * (1 - TR1) * np.power(TA1, 0.25)
                + Ba * F1 * TR1 * (1 - np.power(TAS1, 0.25))
            )
        )
        Edp1_cloud = Edp1 * TC_dif
        # multiple reflections between the ground and the atmosphere
        Edd1 = rg * rs1 * (Ebn1 * np.cos(zenith_angle) + Edp1) / (1 - rg * rs1)
        Edd1_cloud = (
            rg
            * rs1
            * (Ebn1_cloud * np.cos(zenith_angle) + Edp1_cloud)
            / (1 - rg * rs1)
        )

        clear_sky = BandIrradianceResults(
            direct_beam=Ebn1,
            diffuse_on_absorbing_ground=Edp1,
            multiple_reflections=Edd1,
        )
        cloud_sky = BandIrradianceResults(
            direct_beam=Ebn1_cloud,
            diffuse_on_absorbing_ground=Edp1_cloud,
            multiple_reflections=Edd1_cloud,
        )

        return clear_sky, cloud_sky

    def _band_2_irradiance(
        self,
        extraterrestrial_radiation: np.ndarray,
        zenith_angle: np.ndarray,
        surface_albedo: np.ndarray,
        radiation: BandRadiationResults,
        transmittance: CloudTransmittanceResults,
    ):
        TR2 = radiation.TR
        Tg2 = radiation.Tg
        To2 = radiation.To
        Tn2 = radiation.Tn
        Tw2 = radiation.Tw
        TA2 = radiation.TA
        Tn2166 = radiation.Tn166
        Tw2166 = radiation.Tw166
        BR2 = radiation.BR
        F2 = radiation.F
        TAS2 = radiation.TAS
        rs2 = radiation.rs
        Ba = radiation.Ba
        if Ba is None:
            raise ValueError(
                "Ba must not be None for band 2 irradiance calculation"
            )
        rg = surface_albedo
        TC_dir = transmittance.direct
        TC_dif = transmittance.diffuse

        E0n2 = extraterrestrial_radiation * 0.51951
        # direct beam irradiance
        Ebn2 = E0n2 * TR2 * Tg2 * To2 * Tn2 * Tw2 * TA2
        Ebn2_cloud = Ebn2 * TC_dir
        # the incident diffuse irradiance on a perfectly absorbing ground
        Edp2 = (
            E0n2
            * np.cos(zenith_angle)
            * To2
            * Tg2
            * Tn2166
            * Tw2166
            * (
                BR2 * (1 - TR2) * np.power(TA2, 0.25)
                + Ba * F2 * TR2 * (1 - np.power(TAS2, 0.25))
            )
        )
        Edp2_cloud = Edp2 * TC_dif
        # multiple reflections between the ground and the atmosphere
        Edd2 = rg * rs2 * (Ebn2 * np.cos(zenith_angle) + Edp2) / (1 - rg * rs2)
        Edd2_cloud = (
            rg
            * rs2
            * (Ebn2_cloud * np.cos(zenith_angle) + Edp2_cloud)
            / (1 - rg * rs2)
        )

        clear_sky = BandIrradianceResults(
            direct_beam=Ebn2,
            diffuse_on_absorbing_ground=Edp2,
            multiple_reflections=Edd2,
        )
        cloud_sky = BandIrradianceResults(
            direct_beam=Ebn2_cloud,
            diffuse_on_absorbing_ground=Edp2_cloud,
            multiple_reflections=Edd2_cloud,
        )

        return clear_sky, cloud_sky

    def _clear_sky_irradiance(
        self,
        zenith_angle: np.ndarray,
        band1_clear_sky: BandIrradianceResults,
        band2_clear_sky: BandIrradianceResults,
    ):
        Ebn1 = band1_clear_sky.direct_beam
        Ebn2 = band2_clear_sky.direct_beam
        Edp1 = band1_clear_sky.diffuse_on_absorbing_ground
        Edp2 = band2_clear_sky.diffuse_on_absorbing_ground
        Edd1 = band1_clear_sky.multiple_reflections
        Edd2 = band2_clear_sky.multiple_reflections

        # direct horizontal irradiance
        Ebh_cs = (Ebn1 + Ebn2) * np.cos(zenith_angle)
        dni_cs = Ebn1 + Ebn2
        # correct for zenith angle
        dni_cs[np.rad2deg(zenith_angle) > 90] = 0
        Ebh_cs[np.rad2deg(zenith_angle) > 90] = 0
        # diffuse horizontal irradiance
        dhi_cs = Edp1 + Edd1 + Edp2 + Edd2
        dhi_cs[np.rad2deg(zenith_angle) > 90] = 0
        # global horizontal irradiance
        ghi_cs = Ebh_cs + dhi_cs

        # ghi with "tracker"
        ghi_tracker_cs = dni_cs + dhi_cs

        # quality control
        lower = 0

        ghi_cs[ghi_cs < lower] = np.nan
        ghi_tracker_cs[ghi_tracker_cs < lower] = np.nan
        dni_cs[dni_cs < lower] = np.nan
        dhi_cs[dhi_cs < lower] = np.nan

        return ghi_cs, ghi_tracker_cs, dni_cs, dhi_cs

    def _cloud_sky_irradiance(
        self,
        zenith_angle: np.ndarray,
        band1_cloud_sky: BandIrradianceResults,
        band2_cloud_sky: BandIrradianceResults,
    ):
        Ebn1_cloud = band1_cloud_sky.direct_beam
        Ebn2_cloud = band2_cloud_sky.direct_beam
        Edp1_cloud = band1_cloud_sky.diffuse_on_absorbing_ground
        Edp2_cloud = band2_cloud_sky.diffuse_on_absorbing_ground
        Edd1_cloud = band1_cloud_sky.multiple_reflections
        Edd2_cloud = band2_cloud_sky.multiple_reflections

        # direct horizontal irradiance
        Ebh = (Ebn1_cloud + Ebn2_cloud) * np.cos(zenith_angle)
        dni = Ebn1_cloud + Ebn2_cloud
        # correct for zenith angle
        dni[np.rad2deg(zenith_angle) > 90] = 0
        Ebh[np.rad2deg(zenith_angle) > 90] = 0
        # diffuse horizontal irradiance
        dhi = Edp1_cloud + Edd1_cloud + Edp2_cloud + Edd2_cloud
        dhi[np.rad2deg(zenith_angle) > 90] = 0
        # global horizontal irradiance
        ghi = Ebh + dhi

        # ghi with "tracker"
        ghi_tracker = dni + dhi

        # quality control
        lower = 0
        ghi[ghi < lower] = np.nan
        ghi_tracker[ghi_tracker < lower] = np.nan
        dni[dni < lower] = np.nan
        dhi[dhi < lower] = np.nan
        return ghi, ghi_tracker, dni, dhi

    def _internal_convert_radiation(
        self,
        extraterrestrial_radiation: np.ndarray,
        zenith_angle: np.ndarray,
        angstrom_exponent: np.ndarray,
        pressure: np.ndarray,
        water_vapour: np.ndarray,
        ozone: np.ndarray,
        nitrogen_dioxide: np.ndarray,
        surface_albedo: np.ndarray,
        optical_depth_550nm: np.ndarray,
        cod: np.ndarray,
        parameters: dict,
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
    ]:
        air_masses = self._evaluate_air_masses(
            zenith_angle, angstrom_exponent, pressure, optical_depth_550nm
        )
        band1_radiation = self._band_1_radiation(
            ozone,
            nitrogen_dioxide,
            water_vapour,
            angstrom_exponent,
            zenith_angle,
            air_masses,
        )
        band2_radiation = self._band_2_radiation(
            water_vapour,
            angstrom_exponent,
            zenith_angle,
            air_masses,
        )
        cloud_transmittance = self._cloud_transmittance(
            cod, parameters["mu0"], parameters["g"]
        )

        band1_clear_sky, band1_cloud_sky = self._band_1_irradiance(
            extraterrestrial_radiation,
            zenith_angle,
            surface_albedo,
            band1_radiation,
            cloud_transmittance,
        )
        band2_clear_sky, band2_cloud_sky = self._band_2_irradiance(
            extraterrestrial_radiation,
            zenith_angle,
            surface_albedo,
            band2_radiation,
            cloud_transmittance,
        )

        ghi_cs, ghi_tracker_cs, dni_cs, dhi_cs = self._clear_sky_irradiance(
            zenith_angle, band1_clear_sky, band2_clear_sky
        )
        ghi, ghi_tracker, dni, dhi = self._cloud_sky_irradiance(
            zenith_angle, band1_cloud_sky, band2_cloud_sky
        )

        return (
            ghi,
            ghi_tracker,
            dni,
            dhi,
            ghi_cs,
            ghi_tracker_cs,
            dni_cs,
            dhi_cs,
        )

    def convert_radiation(
        self, parameters: dict = DEFAULT_PARAMETERS
    ) -> REST2Result:
        ghi, ghi_tracker, dni, dhi, ghi_cs, ghi_tracker_cs, dni_cs, dhi_cs = (
            self._internal_convert_radiation(
                self.extraterrestrial_radiation,
                self.zenith_angle,
                self.angstrom_exponent,
                self.pressure,
                self.water_vapour,
                self.ozone,
                self.nitrogen_dioxide,
                self.surface_albedo,
                self.optical_depth_550nm,
                self.cod,
                parameters,
            )
        )

        self.result = self._postprocess_variables(
            ghi, ghi_tracker, dni, dhi, ghi_cs, ghi_tracker_cs, dni_cs, dhi_cs
        )

        return self.result

    @staticmethod
    def _choose_radiation_for_metric(
        result: REST2Result, radiation_type: str
    ) -> pl.DataFrame:
        if radiation_type == "dni":
            return result.dni
        elif radiation_type == "dni_cs":
            return result.dni_cs
        elif radiation_type == "ghi":
            return result.ghi
        elif radiation_type == "ghi_cs":
            return result.ghi_cs
        elif radiation_type == "ghi_tracker":
            return result.ghi_tracker
        elif radiation_type == "ghi_tracker_cs":
            return result.ghi_tracker_cs
        else:
            raise ValueError(f"Unknown radiation type: {radiation_type}")

    def train(
        self, measured: pl.DataFrame, radiation_type: str = "dni"
    ) -> dict:
        parameter_keys = list(self.DEFAULT_PARAMETERS.keys())
        parameter_initial_values = np.array(
            [self.DEFAULT_PARAMETERS[key] for key in parameter_keys]
        )

        def f(params: np.ndarray) -> float:
            params_dict = {
                parameter_keys[i]: params[i] for i in range(len(params))
            }
            result = self.convert_radiation(
                params_dict,
            )
            chosen_radiation = self._choose_radiation_for_metric(
                result, radiation_type
            )
            return rmse(
                np.array(measured["valor"]), np.array(chosen_radiation["valor"])
            )

        res = minimize(f, x0=parameter_initial_values, method="BFGS")
        return {parameter_keys[i]: res.x[i] for i in range(len(parameter_keys))}

    def evaluate(
        self,
        result: REST2Result,
        measured: pl.DataFrame,
        radiation_type: str = "dni",
    ) -> dict:
        chosen_radiation = self._choose_radiation_for_metric(
            result, radiation_type
        )
        metrics = {}
        for metric_name, metric_f in zip(
            ["ME", "MAE", "RMSE"], [me, mae, rmse]
        ):
            metrics[metric_name] = metric_f(
                np.array(measured["valor"]), np.array(chosen_radiation["valor"])
            )

        return metrics
