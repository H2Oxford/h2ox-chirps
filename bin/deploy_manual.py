import yaml

from h2ox.chirps.utils import create_task, deploy_task

if __name__ == "__main__":

    deploy_day = "2022-05-02"

    cfg = yaml.load(open("./queue.yaml"), Loader=yaml.SafeLoader)

    task = create_task(
        cfg=cfg,
        payload=dict(today=deploy_day),
        task_name=deploy_day,
        delay=0,
    )

    deploy_task(cfg, task)
