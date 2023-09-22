# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import argparse
import os
import shutil
import string
import boto3

greengrass_client = boto3.client('greengrassv2')
s3_client = boto3.client('s3')
sts_client = boto3.client('sts')


class ParseKwargs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            key, value = value.split('=')
            getattr(namespace, self.dest)[key] = value


parser = argparse.ArgumentParser()

parser.add_argument('-d', '--components-directory', type=str, required=True)
parser.add_argument('-c', '--components', nargs='+', required=True)
parser.add_argument('-v', '--variables', nargs='*', action=ParseKwargs)


def generate_recipe(component_name, version):
    component_variables = args.variables.copy()
    component_variables['component_version_number'] = version
    component_variables['component_name'] = component_name
    component_variables['artifacts_zip_file_name'] = component_name

    # substitute variables, and generate new recipe file
    with open('{}/recipe-template.yml'.format(args.components_directory), 'r') as input_recipe:
        src = string.Template(input_recipe.read())
        result = src.safe_substitute(component_variables)
        with open('{}/{}.yml'.format(args.components_directory, component_name),
                  'w') as output_recipe:
            output_recipe.write(result)


def create_component_version(component_name):
    print(component_name)
    print(args.components_directory) 
    
    with open('{}/{}.yml'.format(args.components_directory, component_name), 'r') as recipe_file:
        recipe = recipe_file.read().encode()
        print(recipe)
        greengrass_client.create_component_version(
            inlineRecipe=recipe
        )


def get_component_version(component_name, fetch_next_version):
    versions = greengrass_client.list_component_versions(
        arn='arn:aws:greengrass:{}:{}:components:{}'.format(os.environ['AWS_REGION'],
                                                            sts_client.get_caller_identity()['Account'], component_name)
    )['componentVersions']

    if len(versions) == 0:
        versions = greengrass_client.list_component_versions(
            arn='arn:aws:greengrass:{}:aws:components:{}'.format(os.environ['AWS_REGION'],
                                                                 component_name)
        )['componentVersions']

    if len(versions) > 0:
        current_version = versions[0]['componentVersion']
    else:
        return '0.0.0'

    current_versions = current_version.split('.')

    major = int(current_versions[0])
    minor = int(current_versions[1])
    micro = int(current_versions[2])

    if fetch_next_version:
        component_version = '{}.{}.{}'.format(major, minor, micro + 1)
    else:
        component_version = '{}.{}.{}'.format(major, minor, micro)
    return component_version


def archive_upload_artifacts(component_name, next_version):
    shutil.make_archive(base_name='{}'.format(component_name),
                        format='zip',
                        root_dir='{}'.format(args.components_directory),
                        base_dir='artifacts')

    bucket_name = args.variables['s3_path'].split('s3://')[1].split('/')[0]
    key_prefix = args.variables['s3_path'].split("s3://")[1].split('/')[1]

    s3_client.upload_file('{}.zip'.format(component_name), bucket_name,
                          '{}/{}/{}/{}.zip'.format(key_prefix, component_name, next_version, component_name))


if __name__ == "__main__":

    args = parser.parse_args()

    print(args)

    for component in args.components:
        next_component_version = get_component_version(component, True)
        generate_recipe(component, next_component_version)
        archive_upload_artifacts(component, next_component_version)
        create_component_version(component)
