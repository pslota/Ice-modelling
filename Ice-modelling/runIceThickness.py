__author__ = 'ragnarekker'
# -*- coding: utf-8 -*-


import copy
import datetime as dt
import doicethickness as dit
import doparameterization as dp
import ice as ice
import weather as we
import getRegObsdata as gro
import getFiledata as gfd
import getWSklima as gws
import getChartserverdata as gcsd
import makePlots as pts
import constants as const
from setEnvironment import data_path, plot_folder


def calculate_ice_cover_air_temp(inn_column, date, temp, sno, cloud_cover=None):

    icecover = []
    timestep = 60*60*24     # fixed timestep of 24hrs given in seconds
    inn_column.remove_metadata()
    inn_column.remove_time()
    icecover.append(copy.deepcopy(inn_column))

    for i in range(0, len(date), 1):
        if date[i] < inn_column.date:
            i = i + 1
        else:
            if cloud_cover != None:
                out_column = dit.get_ice_thickness_from_surface_temp(inn_column, timestep, sno[i], temp[i], cloud_cover=cloud_cover[i])
            else:
                out_column = dit.get_ice_thickness_from_surface_temp(inn_column, timestep, sno[i], temp[i])
            icecover.append(out_column)
            inn_column = copy.deepcopy(out_column)

    return icecover


def calculate_ice_cover_eb(
        utm33_x, utm33_y, date, temp_atm, prec, prec_snow, cloud_cover, wind, rel_hum, pressure_atm, inn_column=None):
    """

    :param utm33_x:
    :param utm33_y:
    :param date:
    :param temp_atm:
    :param prec:
    :param prec_snow:
    :param cloud_cover:
    :param wind:
    :param inn_column:
    :return:
    """

    if inn_column is None:
        inn_column = ice.IceColumn(date[0], [])

    icecover = []
    time_span_in_sec = 60*60*24     # fixed timestep of 24hrs given in seconds
    inn_column.remove_metadata()
    inn_column.remove_time()
    icecover.append(copy.deepcopy(inn_column))
    energy_balance = []

    age_factor_tau = 0.
    albedo_prim = const.alfa_black_ice

    for i in range(0, len(date), 1):
        print "{0}".format(date[i])
        if date[i] < inn_column.date:
            i = i + 1
        else:
            out_column, eb = dit.get_ice_thickness_from_energy_balance(
                utm33_x=utm33_x, utm33_y=utm33_y, ice_column=inn_column, temp_atm=temp_atm[i],
                prec=prec[i], prec_snow=prec_snow[i], time_span_in_sec=time_span_in_sec,
                albedo_prim=albedo_prim, age_factor_tau=age_factor_tau, wind=wind[i], cloud_cover=cloud_cover[i],
                rel_hum=rel_hum[i], pressure_atm=pressure_atm[i])

            icecover.append(out_column)
            energy_balance.append(eb)
            inn_column = copy.deepcopy(out_column)

            if eb.EB is None:
                age_factor_tau = 0.
                albedo_prim = const.alfa_black_ice
            else:
                age_factor_tau = eb.age_factor_tau
                albedo_prim = eb.albedo_prim

    return icecover, energy_balance


def runOrovannNVE(startDate, endDate):

    # Need datetime objects from now on
    LocationName = 'Otrøvatnet v/Nystuen 971 moh'
    startDate = dt.datetime.strptime(startDate, "%Y-%m-%d")
    endDate = dt.datetime.strptime(endDate, "%Y-%m-%d")

    weather_data_filename = '{0}kyrkjestoelane_vaerdata.csv'.format(data_path)
    date, temp, sno, snotot = gfd.read_weather(startDate, endDate, weather_data_filename)

    #observed_ice_filename = '{0}Otroevann observasjoner 2011-2012.csv'.format(data_path)
    #observed_ice = importColumns(observed_ice_filename)
    observed_ice = gro.get_all_season_ice(LocationName, startDate, endDate)

    icecover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno)

    plot_filename = '{0}Ortovann {1}-{2}.png'.format(plot_folder, startDate.year, endDate.year)
    pts.plot_ice_cover(icecover, observed_ice, date, temp, snotot, plot_filename)


def runOrovannMET(startDate, endDate):

    location_name = 'Otrøvatnet v/Nystuen 971 moh'
    wsTemp = gws.getMetData(54710, 'TAM', startDate, endDate, 0, 'list')
    wsSno  = gws.getMetData(54710, 'SA',  startDate, endDate, 0, 'list')

    date = []
    snotot = []
    temp = []

    for e in wsTemp:
        date.append(e.Date)
        temp.append(e.Value)
    for e in wsSno:
        snotot.append(e.Value)

    sno = dp.delta_snow_from_total_snow(snotot)

    #observed_ice_filename = '{0}Otroevann observasjoner {1}-{2}.csv'.format(data_path, startDate.year, endDate.year)
    #observed_ice = importColumns(observed_ice_filename)
    observed_ice = gro.get_all_season_ice(location_name, startDate, endDate)

    if len(observed_ice) == 0:
        icecover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno)
    else:
        icecover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno)

    # Need datetime objects from now on
    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    plot_filename = '{0}Ortovann MET {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    pts.plot_ice_cover(icecover, observed_ice, date, temp, snotot, plot_filename)


def runOrovannEB(startDate, endDate):

    location_name = 'Otrøvatnet v/Nystuen 971 moh'
    wsTemp = gws.getMetData(54710, 'TAM', startDate, endDate, 0, 'list')
    wsSno  = gws.getMetData(54710, 'SA',  startDate, endDate, 0, 'list')
    wsPrec = gws.getMetData(54710, 'RR',  startDate, endDate, 0, 'list')

    utm33_y = 6802070
    utm33_x = 130513

    temp, date = we.strip_metadata(wsTemp, get_dates=True)
    sno_tot = we.strip_metadata(wsSno)
    prec_snow = dp.delta_snow_from_total_snow(sno_tot)
    prec = we.strip_metadata(wsPrec)
    cloud_cover = dp.clouds_from_precipitation(prec)
    wind = [const.avg_wind_const] * len(date)
    rel_hum = [const.rel_hum_air] * len(date)
    pressure_atm = [const.pressure_atm] * len(date)


    # available_elements = gws.getElementsFromTimeserieTypeStation(54710, 0, 'csv')
    observed_ice = gro.get_all_season_ice(location_name, startDate, endDate)

    ice_cover, energy_balance = calculate_ice_cover_eb(
        utm33_x, utm33_y, date, temp, prec, prec_snow, cloud_cover, wind, rel_hum=rel_hum, pressure_atm=pressure_atm,
        inn_column=copy.deepcopy(observed_ice[0]))

    # Need datetime objects from now on
    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    plot_filename = '{0}Ortovann MET EB {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    # pts.plot_ice_cover(ice_cover, observed_ice, date, temp, sno_tot, plot_filename)
    plot_filename = '{0}Ortovann MET with EB {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    pts.plot_ice_cover_eb(ice_cover, energy_balance, observed_ice, date, temp, sno_tot, plot_filename,
                       prec=prec, wind=wind, clouds=cloud_cover)


def runSemsvannEB(startDate, endDate):
    # TODO: get coordinates from the ObsLocation in regObs
    location_name = 'Semsvannet v/Lo 145 moh'

    wsTemp = gws.getMetData(19710, 'TAM', startDate, endDate, 0, 'list')
    wsSno = gws.getMetData(19710, 'SA', startDate, endDate, 0, 'list')
    wsPrec = gws.getMetData(19710, 'RR', startDate, endDate, 0, 'list')
    wsWind = gws.getMetData(18700, 'FFM', startDate, endDate, 0, 'list')
    wsCC = gws.getMetData(18700, 'NNM', startDate, endDate, 0, 'list')

    utm33_y = 6644410
    utm33_x = 243940

    temp, date = we.strip_metadata(wsTemp, get_dates=True)
    sno_tot = we.strip_metadata(wsSno)
    prec_snow = dp.delta_snow_from_total_snow(sno_tot)
    prec = we.strip_metadata(wsPrec)
    wind = we.strip_metadata(wsWind)
    cloud_cover = we.strip_metadata(wsCC)
    rel_hum = [const.rel_hum_air] * len(date)
    pressure_atm = [const.pressure_atm] * len(date)

    observed_ice = gro.get_all_season_ice(location_name, startDate, endDate)

    ice_cover, energy_balance = calculate_ice_cover_eb(
        utm33_x, utm33_y, date,
        temp, prec, prec_snow, cloud_cover=cloud_cover, wind=wind, rel_hum=rel_hum, pressure_atm=pressure_atm,
        inn_column=copy.deepcopy(observed_ice[0]))

    # Need datetime objects from now on
    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    plot_filename = '{0}Semsvann EB {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    # pts.plot_ice_cover(ice_cover, observed_ice, date, temp, sno_tot, plot_filename)
    plot_filename = '{0}Semsvann MET with EB {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    pts.plot_ice_cover_eb(ice_cover, energy_balance, observed_ice, date, temp, sno_tot, plot_filename, prec=prec, wind=wind, clouds=cloud_cover)
    #plot_filename = '{0}Semsvann MET with EB simple {1}-{2}.png'.format(plot_folder, from_date.year, to_date.year)
    #pts.plot_ice_cover_eb_simple(ice_cover, energy_balance, observed_ice, date, temp, sno_tot, plot_filename)


def runSemsvann(startDate, endDate):

    LocationName = 'Semsvannet v/Lo 145 moh'

    wsTemp = gws.getMetData(19710, 'TAM', startDate, endDate, 0, 'list')
    wsSno = gws.getMetData(19710, 'SA', startDate, endDate, 0, 'list')
    wsCC = gws.getMetData(18700, 'NNM', startDate, endDate, 0, 'list')

    temp, date = we.strip_metadata(wsTemp, True)
    snotot = we.strip_metadata(wsSno, False)
    cc = we.strip_metadata(wsCC, False)

    sno = dp.delta_snow_from_total_snow(snotot)

    #observed_ice_filename = '{0}Semsvann observasjoner {1}-{2}.csv'.format(data_path, startDate[0:4], endDate[0:4])
    #observed_ice = importColumns(observed_ice_filename)
    observed_ice = gro.get_all_season_ice(LocationName, startDate, endDate)
    if len(observed_ice) == 0:
        icecover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        icecover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}Semsvann {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(icecover, observed_ice, date, temp, snotot, plot_filename)


def runHakkloa(startDate, endDate):

    LocationName = 'Hakkloa nord 372 moh'
    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    cs_temp = gcsd.getStationdata('6.24.4','17.1', from_date, to_date, timeseries_type=0)
    cs_sno = gcsd.getGriddata(260150, 6671135, 'fsw', from_date, to_date, timeseries_type=0)
    cs_snotot = gcsd.getGriddata(260150, 6671135, 'sd', from_date, to_date, timeseries_type=0)
    wsCC = gws.getMetData(18700, 'NNM', startDate, endDate, 0, 'list')

    temp, date = we.strip_metadata(cs_temp, True)
    sno = we.strip_metadata(cs_sno, False)
    snotot = we.strip_metadata(cs_snotot, False)
    cc = we.strip_metadata(wsCC, False)

    observed_ice = gro.get_all_season_ice(LocationName, startDate, endDate)

    if len(observed_ice) == 0:
        ice_cover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        ice_cover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}Hakkloa {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(ice_cover, observed_ice, date, temp, snotot, plot_filename)


def runSkoddebergvatnet(startDate, endDate):

    LocationName = 'Skoddebergvatnet - nord 101 moh'
    # Skoddebergvatnet - sør 101 moh
    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    #cs_temp = gcsd.getGriddata('189.3.0','17.1', from_date, to_date)
    cs_temp = gcsd.getGriddata(593273, 7612469, 'tm', from_date, to_date)
    cs_sno = gcsd.getGriddata(593273, 7612469, 'fsw', from_date, to_date)
    cs_snotot = gcsd.getGriddata(593273, 7612469, 'sd', from_date, to_date)
    wsCC = gws.getMetData(87640, 'NNM', startDate, endDate, 0, 'list')  # Harstad Stadion

    temp, date = we.strip_metadata(cs_temp, True)
    sno = we.strip_metadata(cs_sno, False)
    snotot = we.strip_metadata(cs_snotot, False)
    cc = we.strip_metadata(wsCC, False)

    observed_ice = gro.get_all_season_ice(LocationName, startDate, endDate)

    if len(observed_ice) == 0:
        ice_cover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        ice_cover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}Skoddebergvatnet {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(ice_cover, observed_ice, date, temp, snotot, plot_filename)


def runGiljastolsvatnet(startDate, endDate):

    LocationNames = ['Giljastølsvatnet 412 moh', 'Giljastølvatnet sør 412 moh']
    x = -1904
    y = 6553573

    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    #cs_temp = gcsd.getStationdata('189.3.0','17.1', from_date, to_date)
    cs_temp = gcsd.getGriddata(x, y, 'tm', from_date, to_date)
    cs_sno = gcsd.getGriddata(x, y, 'fsw', from_date, to_date)
    cs_snotot = gcsd.getGriddata(x, y, 'sd', from_date, to_date)
    wsCC = gws.getMetData(43010, 'NNM', startDate, endDate, 0, 'list')  # Eik - Hove. Ligger lenger sør men er litt inn i landet.
    #wsCC = getMetData(43010, 'NNM', startDate, endDate, 0, 'list') # Sola (44560) er et alternativ

    temp, date = we.strip_metadata(cs_temp, True)
    sno = we.strip_metadata(cs_sno, False)
    snotot = we.strip_metadata(cs_snotot, False)
    cc = we.strip_metadata(wsCC, False)

    observed_ice = gro.get_all_season_ice(LocationNames, startDate, endDate)

    if len(observed_ice) == 0:
        ice_cover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        ice_cover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}Giljastolsvatnet {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(ice_cover, observed_ice, date, temp, snotot, plot_filename)


def runBaklidammen(startDate, endDate):

    LocationNames = ['Baklidammen 200 moh']
    x = 266550
    y = 7040812

    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    cs_temp = gcsd.getGriddata(x, y, 'tm', from_date, to_date)
    cs_sno = gcsd.getGriddata(x, y, 'fsw', from_date, to_date)
    cs_snotot = gcsd.getGriddata(x, y, 'sd', from_date, to_date)
    wsCC = gws.getMetData(68860, 'NNM', startDate, endDate, 0, 'list')  # TRONDHEIM - VOLL

    temp, date = we.strip_metadata(cs_temp, True)
    sno = we.strip_metadata(cs_sno, False)
    snotot = we.strip_metadata(cs_snotot, False)
    cc = we.strip_metadata(wsCC, False)

    observed_ice = gro.get_all_season_ice(LocationNames, startDate, endDate)

    if len(observed_ice) == 0:
        ice_cover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        ice_cover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}Baklidammen {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(ice_cover, observed_ice, date, temp, snotot, plot_filename)


def runStorvannetHammerfest(startDate, endDate):

    LocationNames = ['Storvannet, 7 moh']
    x = 821340
    y = 7862497

    from_date = dt.datetime.strptime(startDate, "%Y-%m-%d")
    to_date = dt.datetime.strptime(endDate, "%Y-%m-%d")

    cs_temp = gcsd.getGriddata(x, y, 'tm', from_date, to_date)
    cs_sno = gcsd.getGriddata(x, y, 'fsw', from_date, to_date)
    cs_snotot = gcsd.getGriddata(x, y, 'sd', from_date, to_date)
    wsCC = gws.getMetData(95350, 'NNM', startDate, endDate, 0, 'list')  # BANAK - østover innerst i fjorden

    temp, date = we.strip_metadata(cs_temp, True)
    sno = we.strip_metadata(cs_sno, False)
    snotot = we.strip_metadata(cs_snotot, False)
    cc = we.strip_metadata(wsCC, False)

    observed_ice = gro.get_all_season_ice(LocationNames, startDate, endDate)

    if len(observed_ice) == 0:
        ice_cover = calculate_ice_cover_air_temp(ice.IceColumn(date[0], []), date, temp, sno, cc)
    else:
        ice_cover = calculate_ice_cover_air_temp(copy.deepcopy(observed_ice[0]), date, temp, sno, cc)

    plot_filename = '{0}StorvannetHammerfest {1}-{2}.png'.format(plot_folder, startDate[0:4], endDate[0:4])
    pts.plot_ice_cover(ice_cover, observed_ice, date, temp, snotot, plot_filename)


if __name__ == "__main__":

    #runSemsvannEB('2012-12-01', '2013-05-20')
    #runSemsvannEB('2013-11-15', '2014-06-20')
    runSemsvannEB('2014-11-15', '2015-06-20')
    runOrovannEB('2014-11-15', '2015-06-20')

    runSemsvann('2011-11-01', '2012-05-01')
    runSemsvann('2012-11-01', '2013-06-01')
    runSemsvann('2013-11-01', '2014-04-15')
    runSemsvann('2014-11-01', '2015-05-15')

    #runOrovannNVE('2011-11-15', '2012-06-20')
    runOrovannMET('2011-11-15', '2012-06-20')
    runOrovannMET('2012-11-15', '2013-06-20')
    runOrovannMET('2013-11-15', '2014-06-20')
    runOrovannMET('2014-11-15', '2015-06-20')

    runHakkloa('2011-11-01', '2012-06-01')
    runHakkloa('2012-11-01', '2013-06-01')
    runHakkloa('2013-11-01', '2014-06-01')
    runHakkloa('2014-11-01', '2015-06-01')

    runSkoddebergvatnet('2006-11-01', '2007-06-01')
    runSkoddebergvatnet('2007-11-01', '2008-06-01')
    runSkoddebergvatnet('2008-11-01', '2009-06-01')
    runSkoddebergvatnet('2009-11-01', '2010-06-01')
    runSkoddebergvatnet('2010-11-01', '2011-06-01')
    runSkoddebergvatnet('2011-11-01', '2012-06-01')
    runSkoddebergvatnet('2012-11-01', '2013-06-01')
    runSkoddebergvatnet('2013-11-01', '2014-06-01')
    runSkoddebergvatnet('2014-11-01', '2015-06-01')

    runGiljastolsvatnet('2012-11-01', '2013-06-01')
    runGiljastolsvatnet('2013-11-01', '2014-06-01')
    runGiljastolsvatnet('2014-11-01', '2015-06-01')

    runBaklidammen('2006-11-01', '2007-06-01')
    runBaklidammen('2007-11-01', '2008-06-01')
    runBaklidammen('2008-11-01', '2009-06-01')
    runBaklidammen('2009-11-01', '2010-06-01')
    runBaklidammen('2010-11-01', '2011-06-01')
    runBaklidammen('2011-11-01', '2012-06-01')
    runBaklidammen('2012-11-01', '2013-06-01')
    runBaklidammen('2013-11-01', '2014-06-01')
    runBaklidammen('2014-11-01', '2015-06-01')

    runStorvannetHammerfest('2008-11-01', '2009-06-01')
    runStorvannetHammerfest('2009-11-01', '2010-06-01')
    runStorvannetHammerfest('2010-11-01', '2011-06-01')
    runStorvannetHammerfest('2011-11-01', '2012-06-01')
    runStorvannetHammerfest('2012-11-01', '2013-06-01')
    runStorvannetHammerfest('2013-11-01', '2014-06-01')
    runStorvannetHammerfest('2014-11-01', '2015-06-01')

