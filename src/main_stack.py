from aws_cdk import (
    Stack,
    Duration,
    aws_timestream as ts,
    aws_iam as iam,
)
import cdk_aws_iotfleetwise as ifw
import re
from src.vehicle_ec2_sim import VehicleEc2Sim
from src.grafana import Grafana
from constructs import Construct


class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = iam.Role(self, "MyRole",
                        assumed_by=iam.ServicePrincipal("iotfleetwise.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
                        ])

        database_name = "FleetWise"
        table_name = "FleetWise"
        database = ts.CfnDatabase(self, "MyDatabase",
                                  database_name=database_name)

        table = ts.CfnTable(self, "MyTable",
                            database_name=database_name,
                            table_name=table_name)

        table.node.add_dependency(database)

        nodes = [ifw.SignalCatalogBranch('Vehicle', 'Vehicle')]
        signals_map_model_a = {}
        with open('data/hscan.dbc') as f:
            lines = f.readlines()
            for line in lines:
                found = re.search(r'^\s+SG_\s+(\w+)\s+.*', line)
                if found:
                    signal_name = found.group(1)
                    nodes.append(ifw.SignalCatalogSensor(signal_name, f'Vehicle.{signal_name}', 'DOUBLE'))
                    signals_map_model_a[signal_name] = f'Vehicle.{signal_name}'
                    
        signals_map_model_b = {}
        with open('data/hscan_sim.dbc') as f:
            lines = f.readlines()
            for line in lines:
                found = re.search(r'^\s+SG_\s+(\w+)\s+.*', line)
                if found:
                    signal_name = found.group(1)
                    nodes.append(ifw.SignalCatalogSensor(signal_name, f'Vehicle.{signal_name}', 'DOUBLE'))
                    signals_map_model_b[signal_name] = f'Vehicle.{signal_name}'

        signal_catalog = ifw.SignalCatalog(self, "FwSignalCatalog",
                                           description='my signal catalog',
                                           role=role,
                                           database=database,
                                           table=table,
                                           nodes=nodes)

        with open('data/hscan.dbc') as f:
            model_a = ifw.VehicleModel(self, 'ModelA',
                                       signal_catalog=signal_catalog,
                                       name='modelA',
                                       description='Model A vehicle',
                                       network_interfaces=[ifw.CanVehicleInterface('1', 'vcan0')],
                                       network_file_definitions=[ifw.CanDefinition(
                                           '1',
                                           signals_map_model_a,
                                           [f.read()])])

        vin100 = ifw.Vehicle(self, 'vin100',
                             vehicle_id='vin100',
                             vehicle_model=model_a,
                             create_iot_thing=True)

        with open('data/hscan_sim.dbc') as f:
            model_b = ifw.VehicleModel(self, 'ModelB',
                                       signal_catalog=signal_catalog,
                                       name='modelB',
                                       description='Model B vehicle',
                                       network_interfaces=[ifw.CanVehicleInterface('1', 'vcan0')],
                                       network_file_definitions=[ifw.CanDefinition(
                                           '1',
                                           signals_map_model_b,
                                           [f.read()])])

        vin200 = ifw.Vehicle(self, 'vin200',
                             vehicle_id='vin200',
                             vehicle_model=model_b,
                             create_iot_thing=True)

        VehicleEc2Sim(self, 'vin200Sim', vehicle=vin200)

        ifw.Fleet(self, 'fleet1',
                  fleet_id='fleet1',
                  signal_catalog=signal_catalog,
                  description='my fleet1',
                  vehicles=[vin100, vin200])

        ifw.Campaign(self, 'CampaignV2001',
                     name='FwTimeBasedCampaignV2001',
                     target=vin200,
                     collection_scheme=ifw.TimeBasedCollectionScheme(Duration.seconds(10)),
                     signals=[
                         ifw.CampaignSignal('Vehicle.EngineTorque'),
                         ifw.CampaignSignal('Vehicle.BrakePedalPressure'),
                     ],
                     auto_approve=True)

        Grafana(self, 'Grafana')
