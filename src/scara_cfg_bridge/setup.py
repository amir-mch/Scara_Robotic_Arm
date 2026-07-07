from setuptools import find_packages, setup

package_name = 'scara_cfg_bridge'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='amir',
    maintainer_email='amir@todo.todo',
    description='SCARA Robot ROS2 Bridge and GUI Dashboard',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bridge_node = scara_cfg_bridge.bridge_node:main',
            'gui_node = scara_cfg_bridge.gui_node:main',
        ],
    },
)
