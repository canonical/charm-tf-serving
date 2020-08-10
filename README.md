# Charmed TensorFlow Serving

## Deploying

To deploy TensorFlow Serving with a model, start by deploying the charm. For a single model, it
will look something like this:

    juju deploy cs:~kubeflow-charmers/tf-serving \
        --storage models=$NAME_OF_STORAGE_CLASS,, \
        --config model-name=/path/to/base/dir/model-name
        --config model-base-path=relative/path/to/model

For multiple models, you can specify a configuration file like this:

    juju deploy cs:~kubeflow-charmers/tf-serving \
        --storage models=$NAME_OF_STORAGE_CLASS,,
        --config model-conf=/path/to/model.conf

For both of these, change `$NAME_OF_STORAGE_CLASS` to the name of a storage class available on
the Kubernetes cluster that you're deploying this charm to. To list available storage classes,
you can run `juju list-storage-pools`. For example, you would replace `$NAME_OF_STORAGE_CLASS`
with `kubernetes` with the below listing:

```
$ juju list-storage-pools
Name        Provider    Attrs
kubernetes  kubernetes  
```

Next, you will need to copy the files onto the storage device backing the workload pod. How you
do this will vary by type of storage class used. For a simple example, see the full MicroK8s
example below.

## MicroK8s example

To start, clone this git repository locally https://github.com/tensorflow/serving:

    git clone https://github.com/tensorflow/serving.git

It has example models that we'll be deploying down below.

Then, ensure that you've enabled storage in MicroK8s:

    microk8s.enable storage

Next, deploy the charm:

    juju deploy cs:~kubeflow-charmers/tf-serving \
        --storage models=kubernetes,, \
        --config model-name=saved_model_half_plus_two_cpu \
        --config model-base-path=testdata/saved_model_half_plus_two_cpu

You can use any of the models stored in the repository under
`tensorflow_serving/servables/tensorflow/testdata/`, instead of `saved_model_half_plus_two_cpu`
if you'd like, just deploy the charm with `model-name` and `model-base-path` configured
appropriately.

Next you'll need to load the models into the pod. In MicroK8s, you can do this easily by
copying files to the pod's volume located under the default storage location of
`/var/snap/microk8s/common/default-storage/`. The volume will have a name in the form of
`$NAMESPACE-$PVC-pvc-*`. You should substitute in the name of the model that you
deployed the charm to for `$NAMESPACE`, and `$PVC` can be found with this command:

    microk8s.kubectl get pods -n $NAMESPACE tf-serving-0 -o=jsonpath="{.spec.volumes[0].persistentVolumeClaim.claimName}"

So, to copy over the files that you cloned earlier, you can run a command that looks like this:

    cp -r serving/tensorflow_serving/servables/tensorflow/testdata /var/snap/microk8s/common/default-storage/kubeflow-models-12345678-tf-serving-0-pvc-1234-5678/

TensorFlow Serving should then see the files and start serving them. You can contact TensorFlow
Serving by getting the IP address of the associated Service:

    $ microk8s.kubectl get -n kubeflow service/tf-serving -o=jsonpath='{.spec.clusterIP}'
    10.152.183.131

And then contacting it via that address:

    # Check on the status of the model
    $ curl http://10.152.183.131:9001/v1/models/saved_model_half_plus_two_cpu
    {
     "model_version_status": [
      {
       "version": "123",
       "state": "AVAILABLE",
       "status": {
        "error_code": "OK",
        "error_message": ""
       }
      }
     ]
    }

    # Use the model to predict some data points
    $ curl http://10.152.183.131:9001/v1/models/saved_model_half_plus_two_cpu:predict -d '{"instances": [1, 2, 3]}'
    {
        "predictions": [2.5, 3.0, 3.5]
    }

## General Kubernetes example

If you're using a Kubernetes cluster that doesn't support simply copying files over, you can
deploy this charm as above, and then copy the files manually with `kubectl cp`:

    # Start by cloning the example serving artifacts
    git clone https://github.com/tensorflow/serving.git

    # Ensure that you have your `kubeconfig` set up properly. For example, with Charmed Kubernetes:
    juju scp -m default kubernetes-master/0:~/config ~/.kube/config

    # Then copy the files to the tf-serving pod
    kubectl cp -n kubeflow serving/tensorflow_serving/servables/tensorflow/testdata tf-serving-0:/models/

After you've copied the files over, you can interact with tf-serving by port forwarding:

    kubectl port-forward -n kubeflow service/tf-serving 9001:9001

TensorFlow Serving will then be available at `localhost`:

    $ curl http://localhost:9001/v1/models/saved_model_half_plus_two_cpu:predict -d '{"instances": [1, 2, 3]}'
    {
        "predictions": [2.5, 3.0, 3.5]
    }

