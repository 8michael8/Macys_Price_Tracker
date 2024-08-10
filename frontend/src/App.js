import React, { useState, useEffect } from 'react';
import './App.css';
import { v4 as uuidv4 } from 'uuid';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';
import magnifying from './pictures/magnifying.png'
import search from './pictures/search.png'
import cement from './pictures/cement.png'

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [checkedItems, setCheckedItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);

  const getDeviceId = () => {
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId = uuidv4();
      localStorage.setItem('device_id', deviceId);
    }
    return deviceId;
  };
  const deviceId = getDeviceId();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response1 = await fetch(`/get_data?device_id=${deviceId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        if (!response1.ok) {
          throw new Error('Network response was not ok. Please restart');
        }
        const data1 = await response1.json();
        setCheckedItems(data1);
      } catch (error) {
        setError(error);
        console.error('Error', error);
      }
    };

    fetchData(); // Call the fetchData function
  }, [deviceId]);

  const handleSubmit = (event) => {
    event.preventDefault();
    setLoading(true);
    document.body.classList.add('no-scroll');
    setError(null);

    fetch("/scrape", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ keyword: keyword })
    })
    .then(res => {
      if (!res.ok) {
        throw new Error("Network response was not ok. Please restart");
      }
      return res.json();
    })
    .then(data => {
      const jobId = data.job_id;
      checkJobStatus(jobId);
      document.body.classList.remove('no-scroll');
    })
    .catch(error => {
      setError(error);
      setLoading(false);
      console.error("There was a problem with the fetch operation:", error);
    });
  };

  const checkJobStatus = (jobId) => {
    fetch(`/get_job/${jobId}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'finished') {
          setData(data.result);
          setLoading(false);
        } else {
          setTimeout(() => checkJobStatus(jobId), 1000);
        }
      })
      .catch(error => {
        setError(error);
        setLoading(false);
        console.error("There was a problem with the fetch operation:", error);
      });
  };

  const handleCheckboxChange = async (event, item) => {
    event.stopPropagation(); // Prevent the click event from bubbling up to the div
    const updatedCheckedItems = isItemChecked(item)
      ? checkedItems.filter(checkedItem => checkedItem.product_name !== item.product_name)
      : [...checkedItems, item];

    setCheckedItems(updatedCheckedItems);

    // Send updated checkedItems to the server
    try {
      const response = await fetch(`/gather?device_id=${deviceId}`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedCheckedItems)
      });
      if (!response.ok) {
        throw new Error("Network response was not ok. Please restart");
      }
    } catch (error) {
      setError(error);
      console.error("Error", error);
    }
  };


  const deleteItem = async (item) => {
    const updatedCheckedItems = checkedItems.filter(checkedItem => checkedItem.product_name !== item.product_name);
    setCheckedItems(updatedCheckedItems);

    // Send updated checkedItems to the server
    try {
      const response = await fetch(`/gather?device_id=${deviceId}`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedCheckedItems)
      });
      if (!response.ok) {
        throw new Error("Network response was not ok. Please restart");
      }
    } catch (error) {
      setError(error);
      console.error("Error", error);
    }
  };

  const isItemChecked = (item) => {
    return checkedItems.some(checkedItem => checkedItem.product_name === item.product_name);
  };

  const handleClick = (item) => {
    setSelectedItem(item);
    document.body.classList.add('no-scroll');
  };

  const handleClose = () => {
    setSelectedItem(null);
    document.body.classList.remove('no-scroll');
  };

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  const convertPriceToNumber = (price) => {
    console.log(price);
    if (typeof price === 'number') {
      return price;
    }

    if (typeof price === 'string') {
      const number = parseFloat(price.replace(/[^0-9.-]+/g, ""));
      if (isNaN(number)) {
        return 0;
      }
      return number;
    }

    return 0;
  };

  const convertListToNumber = (prices) => {
    const priceList = [];

    prices.forEach(priceEntry => {
      priceList.push(convertPriceToNumber(priceEntry.price));
    });
    console.log(priceList)
    return priceList;
  };

  return (
      <div>
        <div className={`${loading ? 'loadingScreen' : 'loadingScreen2'}`}>
          <img src={magnifying} alt="Star" className="magnifying"/>
          <h1 className = "starLoad">★</h1>
          <h1 className="loading"> LOADING <span>(Estimate: 1 Min)</span></h1>
        </div>
        <div className="savedProducts">
          <h1 className="title">macy<span className="star">★</span>s</h1>
          <h2>PRICE TRACKER</h2>
          <div className="titleBorder">
          </div>
          <div className = "savedText">
          <h1>SAVED ITEMS:</h1>
          {checkedItems.length <= 0 && (
              <div className="noItems">
                <p>It looks like you have no saved items. Try searching for a product on the right.</p>
              </div>
          )}
            </div>
          {checkedItems.length > 0 && (
              <ul>
                {checkedItems.map((item, index) => (
                    <li key={index}>
                      <div className='saved' onClick={() => handleClick(item)}>
                        <input
                            type="checkbox"
                            id={`checkbox-${index}`}
                            checked={isItemChecked(item)} // Control the checked status
                            onChange={(e) => handleCheckboxChange(e, item)} // Handle change event
                            onClick={(e) => e.stopPropagation()}
                        />


                        <strong>Brand:</strong> {item.brand_name}<br/>
                        <strong>Product:</strong> {item.product_name}<br/>
                        <strong>Original
                          Price:</strong> {convertPriceToNumber(item.original_price).toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD'
                      })}<br/>
                        <strong>Sale Price:</strong> {convertPriceToNumber(item.sale_price).toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD'
                      })}<br/>
                        <strong>Rating:</strong> {item.rating}<br/>
                        <strong>Reviews:</strong> {item.number_of_reviews}<br/>
                        <strong>Link:</strong> <a href={item.product_link}>Product Link</a>
                        <br/><br/>
                        <button className="delete"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteItem(item);
                                }}
                        >
                          Delete
                        </button>

                        <button className="info"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleClick(item);
                                }}
                        >
                          Price History
                        </button>
                      </div>
                    </li>
                ))}
              </ul>
          )}
        </div>
        {selectedItem && (
            <div className="popup">
              <div className="popup-content">
                <button className="close-button" onClick={handleClose}>X</button>
                <div className="text">
                  <h1>Product Details</h1>
                  <div className="innerText">
                    <strong>Brand:</strong> {selectedItem.brand_name}<br/>
                    <strong>Product:</strong> {selectedItem.product_name}<br/>
                    <strong>Original
                      Price:</strong> {convertPriceToNumber(selectedItem.original_price).toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD'
                  })}<br/>
                    <strong>Sale
                      Price:</strong> {convertPriceToNumber(selectedItem.sale_price).toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD'
                  })}<br/>
                    <strong>Rating:</strong> {selectedItem.rating}<br/>
                    <strong>Reviews:</strong> {selectedItem.number_of_reviews}<br/>
                    <strong>Link:</strong> <a href={selectedItem.product_link}>Product Link</a>
                  </div>
                  <div className="chart-container">
                    <Line
                        data={{
                          labels: selectedItem.prices ? selectedItem.prices.map(priceEntry => new Date(priceEntry.date).toISOString().split('T')[0]) : [new Date().toISOString().split('T')[0]],
                          datasets: [{
                            label: 'Price of Product Over Time',
                            data: selectedItem.prices ? convertListToNumber(selectedItem.prices) : [convertPriceToNumber(selectedItem.sale_price)],
                            backgroundColor: 'aqua',
                            borderColor: 'black',
                            pointBorderColor: 'aqua',
                            showLine: true
                          }]
                        }}
                        options={{
                          plugins: {
                            legend: {
                              display: true
                            }
                          },
                          scales: {
                            y: {
                              min: 0,
                              max: 200
                            }
                          }
                        }}
                    ></Line>
                  </div>
                </div>
              </div>
            </div>
        )}
        <div className="productSearch">
          <img src = {cement} className = "background" alt ="background"/>

          <div className = "search">
          <form onSubmit={handleSubmit} className = "search-bar">
            <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="Search Product or WebID"
            />
            <button type="submit"><img src={search}/></button>
          </form>
            </div>


          {data.length > 0 && (
              <ul>
                {data.map((item, index) => (
                    <li key={index}>
                      <div className="product">
                        <input
                            type="checkbox"
                            id={`checkbox-${index}`}
                            checked={isItemChecked(item)} // Control the checked status
                            onChange={(e) => handleCheckboxChange(e, item)} // Handle change event
                            onClick={(e) => e.stopPropagation()}
                        />
                        <label htmlFor={`checkbox-${index}`}>
                          <strong>Brand:</strong> {item.brand_name}<br/>
                          <strong>Product:</strong> {item.product_name}<br/>
                          <strong>Original
                            Price:</strong> {convertPriceToNumber(item.original_price).toLocaleString('en-US', {
                          style: 'currency',
                          currency: 'USD'
                        })}<br/>
                          <strong>Sale Price:</strong> {convertPriceToNumber(item.sale_price).toLocaleString('en-US', {
                          style: 'currency',
                          currency: 'USD'
                        })}<br/>
                          <strong>Rating:</strong> {item.rating}<br/>
                          <strong>Reviews:</strong> {item.number_of_reviews}<br/>
                          <strong>Link:</strong> <a href={item.product_link}>Product Link</a>
                        </label>
                      </div>
                    </li>
                ))}
              </ul>
          )}
        </div>
      </div>
  );
}

export default App;
